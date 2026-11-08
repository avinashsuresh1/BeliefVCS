use crate::model_client::{ChatMessage, HealthCheckResult, ModelClient, ModelConfig};
use crate::vcs_watcher::{
    CommitItem, CompilationItem, GraphData, ObservationItem, PropositionItem, TerritoryCard, VaultStatus,
    VcsWatcher,
};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SaveTerritoryInput {
    pub id: Option<String>,
    pub territory: String,
    pub guide: String,
    #[serde(default)]
    pub treasures: Vec<ObservationItem>,
    #[serde(default)]
    pub dead_ends: Vec<ObservationItem>,
    #[serde(default)]
    pub known_hazards: Vec<ObservationItem>,
    #[serde(default)]
    pub propositions: Vec<PropositionItem>,
    #[serde(default)]
    pub tags: Vec<String>,
    pub author_agent_id: Option<String>,
    pub branch: Option<String>,
    pub commit_message: Option<String>,
}

/// Resolve vault path safely whether executed from root, desktop/, or src-tauri/
fn resolve_vault_path(raw_path: &str) -> PathBuf {
    let p = PathBuf::from(raw_path);
    if p.exists() {
        return p;
    }
    let parent = PathBuf::from("..").join(raw_path);
    if parent.exists() {
        return parent;
    }
    let grandparent = PathBuf::from("../..").join(raw_path);
    if grandparent.exists() {
        return grandparent;
    }
    p
}

#[tauri::command]
pub fn get_vault_status(vault_path: String) -> Result<VaultStatus, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_status(&path))
}

#[tauri::command]
pub fn list_branches(vault_path: String) -> Result<Vec<String>, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::list_branches(&path))
}

#[tauri::command]
pub fn get_territories(vault_path: String, branch: Option<String>) -> Result<Vec<TerritoryCard>, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_territories(&path, branch.as_deref()))
}

#[tauri::command]
pub fn get_commit_history(vault_path: String) -> Result<Vec<CommitItem>, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_commits(&path))
}

#[tauri::command]
pub fn get_compilations(vault_path: String) -> Result<Vec<CompilationItem>, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_compilations(&path))
}

#[tauri::command]
pub fn get_knowledge_graph(vault_path: String, branch: Option<String>) -> Result<GraphData, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_knowledge_graph(&path, branch.as_deref()))
}

#[tauri::command]
pub async fn test_model_connection(config: ModelConfig) -> Result<HealthCheckResult, String> {
    Ok(ModelClient::check_health(&config).await)
}

#[tauri::command]
pub async fn send_agent_prompt(
    config: ModelConfig,
    prompt: String,
    history: Option<Vec<ChatMessage>>,
    vault_path: String,
) -> Result<String, String> {
    let path = resolve_vault_path(&vault_path);
    let status = if path.exists() {
        VcsWatcher::get_status(&path)
    } else {
        VaultStatus {
            current_branch: "main".to_string(),
            branches: vec!["main".to_string()],
            total_territories: 0,
            total_commits: 0,
            total_compilations: 0,
        }
    };

    let territories = if path.exists() {
        VcsWatcher::get_territories(&path, Some(&status.current_branch))
    } else {
        vec![]
    };

    let context_summary = territories
        .iter()
        .map(|t| format!("- Territory: {}\n  Guide: {}", t.territory, t.guide))
        .collect::<Vec<_>>()
        .join("\n");

    let system_prompt = format!(
        "You are an AI Agent operating within the BeliefVCS framework.\n\
        Epistemic Principle: There are no facts, only beliefs given evidence. Knowledge is WIP always.\n\n\
        Current Knowledge Store Branch: {}\n\
        Known Territories in status quo:\n{}\n\n\
        When solving tasks, follow the Scientific Method:\n\
        1. Query status quo.\n\
        2. Propose hypotheses on an exploration branch if an anomaly occurs.\n\
        3. Compile and verify with empirical evidence before deploying to main.",
        status.current_branch, context_summary
    );

    let mut messages = vec![ChatMessage {
        role: "system".to_string(),
        content: system_prompt,
    }];

    if let Some(hist) = history {
        for msg in hist {
            if msg.role != "system" {
                messages.push(msg);
            }
        }
    }

    let last_matches_prompt = messages
        .last()
        .map(|m| m.role == "user" && m.content == prompt)
        .unwrap_or(false);

    if !last_matches_prompt && !prompt.trim().is_empty() {
        messages.push(ChatMessage {
            role: "user".to_string(),
            content: prompt,
        });
    }

    ModelClient::chat_completion(&config, &messages).await
}

#[tauri::command]
pub fn save_territory(vault_path: String, input: SaveTerritoryInput) -> Result<String, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        std::fs::create_dir_all(&path).map_err(|e| e.to_string())?;
    }

    let branch = input
        .branch
        .clone()
        .unwrap_or_else(|| VcsWatcher::get_current_branch(&path));

    let sanitized_branch = VcsWatcher::sanitize_branch_name(&branch)
        .ok_or_else(|| format!("Invalid branch name: {}", branch))?;

    let territory_id = match input.id.as_deref() {
        Some(s) if !s.trim().is_empty() => s.trim().to_string(),
        _ => {
            let now = chrono::Utc::now();
            let duration = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default();
            format!(
                "{:08x}-{:04x}-4{:03x}-a{:03x}-{:012x}",
                now.timestamp() as u32,
                (now.timestamp_subsec_millis() & 0xffff) as u16,
                (now.timestamp_subsec_micros() & 0xfff) as u16,
                (now.timestamp_subsec_nanos() & 0xfff) as u16,
                duration.as_nanos() as u64 & 0xffffffffffff
            )
        }
    };

    let mut yaml = String::new();
    yaml.push_str("---\n");
    yaml.push_str(&format!("id: {}\n", territory_id));
    yaml.push_str(&format!("territory: {}\n", input.territory));

    if !input.treasures.is_empty() {
        yaml.push_str("treasures:\n");
        for t in &input.treasures {
            yaml.push_str(&format!("- description: {}\n", t.description));
            if let Some(r) = &t.rationale {
                yaml.push_str(&format!("  rationale: {}\n", r));
            } else {
                yaml.push_str("  rationale: null\n");
            }
        }
    }

    if !input.dead_ends.is_empty() {
        yaml.push_str("dead_ends:\n");
        for d in &input.dead_ends {
            yaml.push_str(&format!("- description: {}\n", d.description));
            if let Some(r) = &d.rationale {
                yaml.push_str(&format!("  rationale: {}\n", r));
            } else {
                yaml.push_str("  rationale: null\n");
            }
        }
    }

    if !input.known_hazards.is_empty() {
        yaml.push_str("known_hazards:\n");
        for h in &input.known_hazards {
            yaml.push_str(&format!("- description: {}\n", h.description));
            if let Some(r) = &h.rationale {
                yaml.push_str(&format!("  rationale: {}\n", r));
            } else {
                yaml.push_str("  rationale: null\n");
            }
        }
    }

    if !input.propositions.is_empty() {
        yaml.push_str("propositions:\n");
        for p in &input.propositions {
            yaml.push_str(&format!("- claim: {}\n", p.claim));
            if !p.premises.is_empty() {
                yaml.push_str("  premises:\n");
                for prem in &p.premises {
                    yaml.push_str(&format!("  - {}\n", prem));
                }
            } else {
                yaml.push_str("  premises: []\n");
            }
            if let Some(r) = &p.rationale {
                yaml.push_str(&format!("  rationale: {}\n", r));
            } else {
                yaml.push_str("  rationale: null\n");
            }
            yaml.push_str(&format!("  status: {}\n", p.status));
        }
    }

    if !input.tags.is_empty() {
        yaml.push_str("tags:\n");
        for tag in &input.tags {
            yaml.push_str(&format!("- {}\n", tag));
        }
    }

    if let Some(author) = &input.author_agent_id {
        yaml.push_str(&format!("author_agent_id: {}\n", author));
    }

    yaml.push_str("---\n\n");
    yaml.push_str("# Guide\n");
    yaml.push_str(&input.guide);
    yaml.push('\n');

    let vcs_dir = path.join(".vcs");
    let branches_dir = vcs_dir.join("branches");
    let commits_dir = vcs_dir.join("commits");
    std::fs::create_dir_all(&branches_dir).map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&commits_dir).map_err(|e| e.to_string())?;

    let filename = format!("{}.md", territory_id);

    // Save to branch folder
    let branch_folder = branches_dir.join(&sanitized_branch);
    std::fs::create_dir_all(&branch_folder).map_err(|e| e.to_string())?;
    std::fs::write(branch_folder.join(&filename), &yaml).map_err(|e| e.to_string())?;

    // If active branch is current branch or main, also save to working tree
    let current_branch = VcsWatcher::get_current_branch(&path);
    if branch == current_branch || branch == "main" {
        std::fs::write(path.join(&filename), &yaml).map_err(|e| e.to_string())?;
    }

    // Record belief commit
    let now = chrono::Utc::now();
    let duration = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let commit_id = format!(
        "{:08x}-{:04x}-4{:03x}-b{:03x}-{:012x}",
        now.timestamp() as u32,
        (now.timestamp_subsec_millis() & 0xffff) as u16,
        (now.timestamp_subsec_micros() & 0xfff) as u16,
        (now.timestamp_subsec_nanos() & 0xfff) as u16,
        duration.as_nanos() as u64 & 0xffffffffffff
    );

    let commit_msg = input
        .commit_message
        .filter(|m| !m.trim().is_empty())
        .unwrap_or_else(|| format!("Map territory: {}", input.territory));

    let commit_json = serde_json::json!({
        "id": commit_id,
        "parent_id": null,
        "branch": branch,
        "message": commit_msg,
        "author_agent_id": input.author_agent_id.as_deref().unwrap_or("Autonomous Agent"),
        "evidence": null,
        "timestamp": now.timestamp() as f64
    });

    std::fs::write(
        commits_dir.join(format!("{}.json", commit_id)),
        serde_json::to_string_pretty(&commit_json).map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;

    Ok(territory_id)
}

#[tauri::command]
pub async fn distill_unstructured_text(
    config: ModelConfig,
    raw_text: String,
) -> Result<SaveTerritoryInput, String> {
    if raw_text.trim().is_empty() {
        return Err("Cannot distill empty text".to_string());
    }

    let system_prompt = "You are an expert knowledge distillation agent for the BeliefVCS framework.\n\
Your goal is to extract structured engineering/domain knowledge from unstructured text (notes, logs, code documentation, or post-mortems).\n\
Respond with ONLY valid raw JSON with this exact schema (no markdown formatting, no code fences):\n\
{\n\
  \"territory\": \"A concise, descriptive title for the domain/territory\",\n\
  \"guide\": \"Actionable recommended procedural instructions or guidance\",\n\
  \"treasures\": [{\"description\": \"what worked / positive finding\", \"rationale\": \"why it worked\"}],\n\
  \"dead_ends\": [{\"description\": \"what failed / anti-pattern\", \"rationale\": \"why it failed\"}],\n\
  \"known_hazards\": [{\"description\": \"potential hazard or pitfall\", \"rationale\": \"explanation or null\"}],\n\
  \"propositions\": [{\"claim\": \"Formal proven statement\", \"premises\": [\"premise\"], \"rationale\": \"deduction rationale\", \"status\": \"PROVEN\"}],\n\
  \"tags\": [\"tag1\", \"tag2\"]\n\
}";

    let messages = vec![
        ChatMessage {
            role: "system".to_string(),
            content: system_prompt.to_string(),
        },
        ChatMessage {
            role: "user".to_string(),
            content: format!("Unstructured Data to Distill:\n\n{}", raw_text),
        },
    ];

    let raw_response = ModelClient::chat_completion(&config, &messages).await?;

    let trimmed = raw_response.trim();
    let json_str = if trimmed.starts_with("```") {
        let lines: Vec<&str> = trimmed.lines().collect();
        if lines.len() >= 2 && lines.first().unwrap().starts_with("```") && lines.last().unwrap().starts_with("```") {
            lines[1..lines.len() - 1].join("\n")
        } else {
            trimmed.to_string()
        }
    } else {
        trimmed.to_string()
    };

    match serde_json::from_str::<SaveTerritoryInput>(&json_str) {
        Ok(parsed) => Ok(parsed),
        Err(_) => Ok(SaveTerritoryInput {
            id: None,
            territory: "Extracted Territory".to_string(),
            guide: raw_response,
            treasures: vec![],
            dead_ends: vec![],
            known_hazards: vec![],
            propositions: vec![],
            tags: vec!["ingested".to_string()],
            author_agent_id: Some("Distillation Agent".to_string()),
            branch: None,
            commit_message: Some("Ingest distilled knowledge".to_string()),
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolve_vault_path_nonexistent() {
        let p = resolve_vault_path("non_existent_folder_xyz_123");
        assert_eq!(p, PathBuf::from("non_existent_folder_xyz_123"));
    }

    #[test]
    fn test_resolve_vault_path_existing() {
        let p = resolve_vault_path("Cargo.toml");
        assert!(p.exists());
    }

    #[test]
    fn test_save_territory_in_temp_vault() {
        let temp_dir = std::env::temp_dir().join(format!("belief_test_{}", chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0)));
        let _ = std::fs::create_dir_all(&temp_dir);

        let input = SaveTerritoryInput {
            id: None,
            territory: "Rust Concurrency".to_string(),
            guide: "Use Tokio channels and Mutex locks.".to_string(),
            treasures: vec![ObservationItem {
                description: "Mpsc channel".to_string(),
                rationale: Some("Fast message passing".to_string()),
            }],
            dead_ends: vec![ObservationItem {
                description: "Blocking in async context".to_string(),
                rationale: Some("Starves executor".to_string()),
            }],
            known_hazards: vec![],
            propositions: vec![],
            tags: vec!["rust".to_string(), "async".to_string()],
            author_agent_id: Some("Agent_Test".to_string()),
            branch: Some("main".to_string()),
            commit_message: Some("Document concurrency patterns".to_string()),
        };

        let res = save_territory(temp_dir.to_str().unwrap().to_string(), input);
        assert!(res.is_ok());
        let id = res.unwrap();
        assert!(!id.is_empty());

        let file_path = temp_dir.join(format!("{}.md", id));
        assert!(file_path.exists());
        let content = std::fs::read_to_string(&file_path).unwrap();
        assert!(content.contains("territory: Rust Concurrency"));
        assert!(content.contains("Mpsc channel"));
        assert!(content.contains("Blocking in async context"));

        let _ = std::fs::remove_dir_all(temp_dir);
    }
}
