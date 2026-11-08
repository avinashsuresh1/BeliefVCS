use serde::{Deserialize, Serialize};
use std::time::Instant;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelConfig {
    pub provider: String,
    pub base_url: String,
    pub api_key: Option<String>,
    pub model_name: String,
    pub temperature: Option<f32>,
}

impl Default for ModelConfig {
    fn default() -> Self {
        Self {
            provider: "ollama".to_string(),
            base_url: "http://localhost:11434/v1".to_string(),
            api_key: None,
            model_name: "llama3".to_string(),
            temperature: Some(0.2),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Serialize)]
struct OpenAIRequest<'a> {
    model: &'a str,
    messages: &'a [ChatMessage],
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f32>,
}

#[derive(Debug, Deserialize)]
struct OpenAIChoice {
    message: ChatMessage,
}

#[derive(Debug, Deserialize)]
struct OpenAIResponse {
    choices: Option<Vec<OpenAIChoice>>,
    error: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheckResult {
    pub connected: bool,
    pub latency_ms: u64,
    pub message: String,
}

pub struct ModelClient;

impl ModelClient {
    /// Format base URL safely ensuring /chat/completions endpoint
    pub fn get_chat_url(base_url: &str) -> String {
        let trimmed = base_url.trim_end_matches('/');
        if trimmed.ends_with("/chat/completions") {
            trimmed.to_string()
        } else if trimmed.ends_with("/v1") {
            format!("{}/chat/completions", trimmed)
        } else {
            format!("{}/v1/chat/completions", trimmed)
        }
    }

    /// Validate that URL uses http or https scheme to prevent SSRF and protocol misuse
    pub fn validate_url_scheme(url: &str) -> Result<(), String> {
        let trimmed = url.trim();
        if trimmed.starts_with("http://") || trimmed.starts_with("https://") {
            Ok(())
        } else {
            Err(format!(
                "Invalid URL scheme in '{}'. Only http:// and https:// endpoints are permitted.",
                url
            ))
        }
    }

    /// Format models endpoint for health checking
    pub fn get_models_url(base_url: &str) -> String {
        let trimmed = base_url.trim_end_matches('/');
        if trimmed.ends_with("/v1") {
            format!("{}/models", trimmed)
        } else if trimmed.ends_with("/chat/completions") {
            trimmed.replace("/chat/completions", "/models")
        } else {
            format!("{}/v1/models", trimmed)
        }
    }

    /// Check connectivity and latency to any local or cloud AI endpoint
    pub async fn check_health(config: &ModelConfig) -> HealthCheckResult {
        if let Err(e) = Self::validate_url_scheme(&config.base_url) {
            return HealthCheckResult {
                connected: false,
                latency_ms: 0,
                message: e,
            };
        }

        let client = match reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(6))
            .build()
        {
            Ok(c) => c,
            Err(e) => {
                return HealthCheckResult {
                    connected: false,
                    latency_ms: 0,
                    message: format!("Failed to build HTTP client: {}", e),
                }
            }
        };

        let models_url = Self::get_models_url(&config.base_url);
        let start = Instant::now();

        let mut req = client.get(&models_url);
        if let Some(key) = &config.api_key {
            if !key.trim().is_empty() {
                req = req.header("Authorization", format!("Bearer {}", key.trim()));
            }
        }

        match req.send().await {
            Ok(resp) => {
                let latency_ms = start.elapsed().as_millis() as u64;
                if resp.status().is_success() {
                    HealthCheckResult {
                        connected: true,
                        latency_ms,
                        message: format!("Connected to {} ({}) in {}ms", config.provider, config.model_name, latency_ms),
                    }
                } else {
                    HealthCheckResult {
                        connected: false,
                        latency_ms,
                        message: format!("Endpoint responded with status {}: {}", resp.status(), resp.status().canonical_reason().unwrap_or("Unknown")),
                    }
                }
            }
            Err(e) => {
                let latency_ms = start.elapsed().as_millis() as u64;
                HealthCheckResult {
                    connected: false,
                    latency_ms,
                    message: format!("Connection failed: {}", e),
                }
            }
        }
    }

    /// Execute a chat completion across any OpenAI-compatible local/cloud endpoint
    pub async fn chat_completion(
        config: &ModelConfig,
        messages: &[ChatMessage],
    ) -> Result<String, String> {
        Self::validate_url_scheme(&config.base_url)?;

        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(60))
            .build()
            .map_err(|e| format!("Client error: {}", e))?;

        let chat_url = Self::get_chat_url(&config.base_url);

        let payload = OpenAIRequest {
            model: &config.model_name,
            messages,
            temperature: config.temperature,
        };

        let mut req = client.post(&chat_url).json(&payload);

        if let Some(key) = &config.api_key {
            if !key.trim().is_empty() {
                req = req.header("Authorization", format!("Bearer {}", key.trim()));
            }
        }

        let resp = req
            .send()
            .await
            .map_err(|e| format!("Request to {} failed: {}", config.base_url, e))?;

        let status = resp.status();
        let body = resp
            .text()
            .await
            .map_err(|e| format!("Failed to read response body: {}", e))?;

        if !status.is_success() {
            return Err(format!("Model endpoint returned HTTP {}: {}", status, body));
        }

        let parsed: OpenAIResponse = serde_json::from_str(&body)
            .map_err(|e| format!("Failed to parse response JSON: {}. Body: {}", e, body))?;

        if let Some(choices) = parsed.choices {
            if let Some(first) = choices.into_iter().next() {
                return Ok(first.message.content);
            }
        }

        if let Some(err) = parsed.error {
            return Err(format!("Model API error: {}", err));
        }

        Err("No completion choices returned by model.".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chat_url_formatting() {
        assert_eq!(
            ModelClient::get_chat_url("http://localhost:11434/v1"),
            "http://localhost:11434/v1/chat/completions"
        );
        assert_eq!(
            ModelClient::get_chat_url("http://localhost:11434"),
            "http://localhost:11434/v1/chat/completions"
        );
        assert_eq!(
            ModelClient::get_chat_url("https://api.openai.com/v1/chat/completions/"),
            "https://api.openai.com/v1/chat/completions"
        );
    }

    #[test]
    fn test_models_url_formatting() {
        assert_eq!(
            ModelClient::get_models_url("http://localhost:11434/v1"),
            "http://localhost:11434/v1/models"
        );
        assert_eq!(
            ModelClient::get_models_url("https://api.openai.com/v1/chat/completions"),
            "https://api.openai.com/v1/models"
        );
    }

    #[test]
    fn test_model_config_serialization() {
        let cfg = ModelConfig::default();
        let json = serde_json::to_string(&cfg).unwrap();
        let deserialized: ModelConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.provider, "ollama");
        assert_eq!(deserialized.model_name, "llama3");
    }

    #[test]
    fn test_validate_url_scheme() {
        assert!(ModelClient::validate_url_scheme("http://localhost:11434/v1").is_ok());
        assert!(ModelClient::validate_url_scheme("https://api.openai.com/v1").is_ok());
        assert!(ModelClient::validate_url_scheme("ftp://malicious.internal").is_err());
        assert!(ModelClient::validate_url_scheme("file:///etc/passwd").is_err());
        assert!(ModelClient::validate_url_scheme("javascript:alert(1)").is_err());
        assert!(ModelClient::validate_url_scheme("").is_err());
    }
}
