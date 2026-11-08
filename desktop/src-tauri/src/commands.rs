use crate::model_client::{ChatMessage, HealthCheckResult, ModelClient, ModelConfig};
use crate::vcs_watcher::{CommitItem, CompilationItem, GraphData, TerritoryCard, VaultStatus, VcsWatcher};
use std::path::PathBuf;

#[tauri::command]
pub fn get_vault_status(vault_path: String) -> Result<VaultStatus, String> {
    let path = PathBuf::from(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_status(&path))
}

#[tauri::command]
pub fn list_branches(vault_path: String) -> Result<Vec<String>, String> {
    let path = PathBuf::from(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::list_branches(&path))
}

#[tauri::command]
pub fn get_territories(vault_path: String, branch: Option<String>) -> Result<Vec<TerritoryCard>, String> {
    let path = PathBuf::from(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_territories(&path, branch.as_deref()))
}

#[tauri::command]
pub fn get_commit_history(vault_path: String) -> Result<Vec<CommitItem>, String> {
    let path = PathBuf::from(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_commits(&path))
}

#[tauri::command]
pub fn get_compilations(vault_path: String) -> Result<Vec<CompilationItem>, String> {
    let path = PathBuf::from(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    Ok(VcsWatcher::get_compilations(&path))
}

#[tauri::command]
pub fn get_knowledge_graph(vault_path: String, branch: Option<String>) -> Result<GraphData, String> {
    let path = PathBuf::from(&vault_path);
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
    vault_path: String,
) -> Result<String, String> {
    let path = PathBuf::from(&vault_path);
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

    let messages = vec![
        ChatMessage {
            role: "system".to_string(),
            content: system_prompt,
        },
        ChatMessage {
            role: "user".to_string(),
            content: prompt,
        },
    ];

    ModelClient::chat_completion(&config, &messages).await
}
