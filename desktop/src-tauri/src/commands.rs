use crate::model_client::{ChatMessage, HealthCheckResult, ModelClient, ModelConfig};
use crate::vcs_watcher::{
    CommitItem, CompilationItem, GraphData, ObservationItem, PropositionItem, TerritoryCard, VaultStatus,
    VcsWatcher,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};
use std::path::{Path, PathBuf};

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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArgumentAssessment {
    pub assessment: String,
    pub reasoning: String,
    pub supporting_ids: Vec<String>,
    pub counterevidence_ids: Vec<String>,
    pub assumptions: Vec<String>,
    pub testable_predictions: Vec<String>,
}

fn yaml_quote(value: &str) -> Result<String, String> {
    serde_json::to_string(value).map_err(|e| e.to_string())
}

fn validate_argument_assessment(
    assessment: &ArgumentAssessment,
    known_ids: &std::collections::HashSet<String>,
) -> Result<(), String> {
    if !["SUPPORTS", "CHALLENGES", "MIXED", "INSUFFICIENT"]
        .contains(&assessment.assessment.as_str())
    {
        return Err("Model returned an unsupported assessment value".to_string());
    }
    if assessment.reasoning.trim().is_empty() {
        return Err("Model assessment must include reasoning".to_string());
    }
    if assessment
        .supporting_ids
        .iter()
        .chain(assessment.counterevidence_ids.iter())
        .any(|id| !known_ids.contains(id))
    {
        return Err("Model assessment cited a territory ID that is not in the supplied context".to_string());
    }
    if (assessment.assessment == "SUPPORTS" && assessment.supporting_ids.is_empty())
        || (assessment.assessment == "CHALLENGES" && assessment.counterevidence_ids.is_empty())
        || (assessment.assessment == "MIXED"
            && (assessment.supporting_ids.is_empty() || assessment.counterevidence_ids.is_empty()))
    {
        return Err("Model assessment does not provide the required evidence citations".to_string());
    }
    Ok(())
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

fn branch_directory(vault: &Path, branch: &str) -> Result<PathBuf, String> {
    let safe_name = VcsWatcher::sanitize_branch_name(branch)
        .ok_or_else(|| format!("Invalid branch name: {}", branch))?;
    Ok(vault.join(".vcs").join("branches").join(safe_name))
}

fn copy_markdown_files(source: &Path, target: &Path, clear_target: bool) -> Result<(), String> {
    std::fs::create_dir_all(target).map_err(|e| e.to_string())?;
    if clear_target {
        for entry in std::fs::read_dir(target).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            if entry.file_type().map_err(|e| e.to_string())?.is_file()
                && entry.path().extension().map(|ext| ext == "md").unwrap_or(false)
            {
                std::fs::remove_file(entry.path()).map_err(|e| e.to_string())?;
            }
        }
    }
    if source.exists() {
        for entry in std::fs::read_dir(source).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            if entry.file_type().map_err(|e| e.to_string())?.is_file()
                && entry.path().extension().map(|ext| ext == "md").unwrap_or(false)
            {
                std::fs::copy(entry.path(), target.join(entry.file_name()))
                    .map_err(|e| e.to_string())?;
            }
        }
    }
    Ok(())
}

fn sync_working_tree_to_branch(vault: &Path, branch: &str) -> Result<PathBuf, String> {
    let branch_dir = branch_directory(vault, branch)?;
    copy_markdown_files(vault, &branch_dir, true)?;
    Ok(branch_dir)
}

fn sync_branch_to_working_tree(vault: &Path, branch: &str) -> Result<(), String> {
    let branch_dir = branch_directory(vault, branch)?;
    if !branch_dir.is_dir() {
        return Err(format!("Branch does not exist: {}", branch));
    }
    copy_markdown_files(&branch_dir, vault, true)
}

fn read_markdown_snapshot(directory: &Path) -> Result<BTreeMap<String, Vec<u8>>, String> {
    let mut snapshot = BTreeMap::new();
    if !directory.exists() {
        return Ok(snapshot);
    }

    for entry in std::fs::read_dir(directory)
        .map_err(|e| format!("Failed to read {}: {}", directory.display(), e))?
    {
        let entry = entry.map_err(|e| format!("Failed to read knowledge entry: {}", e))?;
        let path = entry.path();
        if entry.file_type().map_err(|e| e.to_string())?.is_file()
            && path.extension().map(|ext| ext == "md").unwrap_or(false)
        {
            let filename = entry.file_name().to_string_lossy().to_string();
            let contents = std::fs::read(&path)
                .map_err(|e| format!("Failed to read knowledge file {}: {}", path.display(), e))?;
            snapshot.insert(filename, contents);
        }
    }
    Ok(snapshot)
}

fn snapshot_digest(directory: &Path) -> Result<String, String> {
    let snapshot = read_markdown_snapshot(directory)?;
    let mut digest = Sha256::new();
    for (filename, contents) in snapshot {
        digest.update(filename.as_bytes());
        digest.update([0]);
        digest.update(contents);
        digest.update([0]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn validate_knowledge_integrity(territories: &[TerritoryCard]) -> Vec<String> {
    let mut errors = Vec::new();
    if territories.is_empty() {
        errors.push("No knowledge records were found on this branch.".to_string());
        return errors;
    }

    let mut ids = HashSet::new();
    let mut names = HashSet::new();
    let mut proposition_ids = HashSet::new();
    for territory in territories {
        if !ids.insert(territory.id.clone()) {
            errors.push(format!("Duplicate territory ID: {}", territory.id));
        }
        let normalized_name = territory.territory.trim().to_lowercase();
        if !names.insert(normalized_name) {
            errors.push(format!("Duplicate territory name: {}", territory.territory));
        }
        if territory.guide.trim().is_empty() {
            errors.push(format!("Territory '{}' has an empty guide.", territory.territory));
        }

        for proposition in &territory.propositions {
            if proposition.claim.trim().is_empty() {
                errors.push(format!("Territory '{}' has an empty proposition.", territory.territory));
            }
            if proposition.id.trim().is_empty() {
                errors.push(format!(
                    "A proposition in '{}' is missing its stable ID.",
                    territory.territory
                ));
            } else if !proposition_ids.insert(proposition.id.clone()) {
                errors.push(format!(
                    "Territory '{}' contains duplicate proposition ID '{}'.",
                    territory.territory, proposition.id
                ));
            }
            if !["CONJECTURE", "ACCEPTED", "LEGACY_PROVEN"]
                .contains(&proposition.status.as_str())
            {
                errors.push(format!(
                    "Proposition '{}' has unsupported status '{}'.",
                    proposition.id, proposition.status
                ));
            }
        }
    }

    for territory in territories {
        for link in &territory.wiki_links {
            if !names.contains(&link.trim().to_lowercase()) {
                errors.push(format!(
                    "Territory '{}' links to missing territory '{}'.",
                    territory.territory, link
                ));
            }
        }
    }
    errors
}

fn store_compilation(vault: &Path, branch: &str, record: &serde_json::Value) -> Result<(), String> {
    let comp_dir = vault.join(".vcs").join("compilations");
    std::fs::create_dir_all(&comp_dir).map_err(|e| e.to_string())?;
    let safe_branch = VcsWatcher::sanitize_branch_name(branch)
        .ok_or_else(|| format!("Invalid branch name: {}", branch))?;
    let record_path = comp_dir.join(format!("{}.json", safe_branch));
    let serialized = serde_json::to_string_pretty(record).map_err(|e| e.to_string())?;
    std::fs::write(record_path, serialized).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_hypothesis_branch(vault_path: String, hypothesis_name: String) -> Result<String, String> {
    let path = resolve_vault_path(&vault_path);
    std::fs::create_dir_all(&path).map_err(|e| e.to_string())?;
    let trimmed = hypothesis_name.trim();
    if trimmed.is_empty() {
        return Err("Hypothesis name cannot be empty".to_string());
    }
    let branch = if trimmed.starts_with("hypothesis/") {
        trimmed.to_string()
    } else {
        format!("hypothesis/{}", trimmed)
    };
    let target_dir = branch_directory(&path, &branch)?;
    if target_dir.exists() {
        return Err(format!("Branch already exists: {}", branch));
    }

    let current = VcsWatcher::get_current_branch(&path);
    let source_dir = sync_working_tree_to_branch(&path, &current)?;
    copy_markdown_files(&source_dir, &target_dir, true)?;
    let base_dir = path
        .join(".vcs")
        .join("bases")
        .join(VcsWatcher::sanitize_branch_name(&branch).ok_or_else(|| "Invalid branch name".to_string())?);
    copy_markdown_files(&source_dir, &base_dir, true)?;
    std::fs::write(path.join(".vcs").join("HEAD"), &branch).map_err(|e| e.to_string())?;
    Ok(branch)
}

#[tauri::command]
pub fn checkout_branch(vault_path: String, branch: String) -> Result<String, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    let current = VcsWatcher::get_current_branch(&path);
    if current == branch {
        let current_dir = branch_directory(&path, &branch)?;
        if !current_dir.is_dir() {
            sync_working_tree_to_branch(&path, &branch)?;
        }
        return Ok(branch);
    }

    let target_dir = branch_directory(&path, &branch)?;
    if !target_dir.is_dir() {
        return Err(format!("Branch does not exist: {}", branch));
    }

    sync_working_tree_to_branch(&path, &current)?;
    sync_branch_to_working_tree(&path, &branch)?;
    std::fs::write(path.join(".vcs").join("HEAD"), &branch).map_err(|e| e.to_string())?;
    Ok(branch)
}

#[tauri::command]
pub fn run_knowledge_integrity_probe(vault_path: String, branch: String) -> Result<CompilationItem, String> {
    let path = resolve_vault_path(&vault_path);
    if !branch.starts_with("hypothesis/") {
        return Err("The built-in integrity probe can only run on a hypothesis branch.".to_string());
    }
    if VcsWatcher::get_current_branch(&path) != branch {
        return Err("Check out the hypothesis branch before running its probe.".to_string());
    }

    let branch_dir = sync_working_tree_to_branch(&path, &branch)?;
    let revision_digest = snapshot_digest(&branch_dir)?;
    let (validation, record_count) = match VcsWatcher::get_territories(&path, Some(&branch)) {
        Ok(territories) => {
            let errors = validate_knowledge_integrity(&territories);
            (errors, territories.len())
        }
        Err(error) => (vec![error], 0),
    };
    let passed = validation.is_empty();
    let exit_code = if passed { 0 } else { 1 };
    let output_log = if passed {
        format!(
            "Validated {} knowledge records for parseability, IDs, proposition statuses, and internal links.\nThis structural check does not evaluate semantic truth.",
            record_count
        )
    } else {
        validation.join("\n")
    };
    let message = if passed {
        "Knowledge-integrity probe PASSED. This is structural evidence, not semantic proof.".to_string()
    } else {
        format!("Knowledge-integrity probe FAILED: {}", validation.join(" "))
    };
    let test_command = "built-in: knowledge-integrity-v1";
    let timestamp = chrono::Utc::now().timestamp() as f64;
    let record = serde_json::json!({
        "passed": passed,
        "message": message,
        "validation_profile": "knowledge-integrity-v1",
        "revision_digest": revision_digest,
        "proof_verification": null,
        "evidence": {
            "test_command": test_command,
            "output_log": output_log,
            "exit_code": exit_code,
            "timestamp": timestamp
        }
    });
    store_compilation(&path, &branch, &record)?;

    Ok(CompilationItem {
        branch,
        passed,
        message: record["message"].as_str().unwrap_or_default().to_string(),
        test_command: test_command.to_string(),
        validation_profile: Some("knowledge-integrity-v1".to_string()),
        revision_digest: Some(record["revision_digest"].as_str().unwrap_or_default().to_string()),
        exit_code,
        proof_sound: None,
        proof_verdict: None,
        proof_violations: Vec::new(),
        candidate_conflicts: Vec::new(),
        supporting_ids: Vec::new(),
        counterevidence_ids: Vec::new(),
    })
}

#[tauri::command]
pub fn merge_hypothesis_to_main(vault_path: String, source_branch: String) -> Result<String, String> {
    let path = resolve_vault_path(&vault_path);
    if !source_branch.starts_with("hypothesis/") {
        return Err("Only hypothesis branches can be integrated into main.".to_string());
    }
    let source_dir = branch_directory(&path, &source_branch)?;
    if !source_dir.is_dir() {
        return Err(format!("Hypothesis branch does not exist: {}", source_branch));
    }
    if VcsWatcher::get_current_branch(&path) == source_branch {
        sync_working_tree_to_branch(&path, &source_branch)?;
    }

    let safe_branch = VcsWatcher::sanitize_branch_name(&source_branch)
        .ok_or_else(|| format!("Invalid branch name: {}", source_branch))?;
    let compilation_path = path
        .join(".vcs")
        .join("compilations")
        .join(format!("{}.json", safe_branch));
    let compilation_text = std::fs::read_to_string(&compilation_path)
        .map_err(|_| "Run the built-in knowledge-integrity probe before integration.".to_string())?;
    let compilation: serde_json::Value = serde_json::from_str(&compilation_text)
        .map_err(|e| format!("Stored probe record is malformed: {}", e))?;
    if compilation["passed"].as_bool() != Some(true)
        || compilation["validation_profile"].as_str() != Some("knowledge-integrity-v1")
    {
        return Err("The latest built-in knowledge-integrity probe did not pass.".to_string());
    }
    let recorded_digest = compilation["revision_digest"]
        .as_str()
        .ok_or_else(|| "Stored probe has no knowledge revision digest.".to_string())?;
    if snapshot_digest(&source_dir)? != recorded_digest {
        return Err("Hypothesis knowledge changed after its probe. Run the probe again.".to_string());
    }

    let base_dir = path.join(".vcs").join("bases").join(&safe_branch);
    if !base_dir.is_dir() {
        return Err("Hypothesis merge base is unavailable; create a fresh branch from the current status quo.".to_string());
    }
    let target_dir = branch_directory(&path, "main")?;
    std::fs::create_dir_all(&target_dir).map_err(|e| e.to_string())?;
    if VcsWatcher::get_current_branch(&path) == "main" {
        sync_working_tree_to_branch(&path, "main")?;
    }

    let base = read_markdown_snapshot(&base_dir)?;
    let source = read_markdown_snapshot(&source_dir)?;
    let target = read_markdown_snapshot(&target_dir)?;
    let mut changes = Vec::new();
    let mut conflicts = Vec::new();
    let filenames: HashSet<String> = base
        .keys()
        .chain(source.keys())
        .chain(target.keys())
        .cloned()
        .collect();
    for filename in filenames {
        let base_contents = base.get(&filename);
        let source_contents = source.get(&filename);
        let target_contents = target.get(&filename);
        if source_contents == base_contents || source_contents == target_contents {
            continue;
        }
        if target_contents == base_contents {
            changes.push((filename, source_contents.cloned()));
        } else {
            conflicts.push(filename);
        }
    }
    if !conflicts.is_empty() {
        conflicts.sort();
        return Err(format!(
            "Integration blocked: both branches changed the same records: {}",
            conflicts.join(", ")
        ));
    }

    for (filename, contents) in changes {
        let target_file = target_dir.join(filename);
        if let Some(contents) = contents {
            std::fs::write(target_file, contents).map_err(|e| e.to_string())?;
        } else if target_file.exists() {
            std::fs::remove_file(target_file).map_err(|e| e.to_string())?;
        }
    }

    if VcsWatcher::get_current_branch(&path) == "main" {
        sync_branch_to_working_tree(&path, "main")?;
    }

    let now = chrono::Utc::now();
    let commit_id = format!("desktop-merge-{}", now.timestamp_nanos_opt().unwrap_or(0));
    let commit = serde_json::json!({
        "id": commit_id,
        "parent_id": null,
        "branch": "main",
        "message": format!("Integrate '{}' after passing knowledge-integrity-v1 probe", source_branch),
        "author_agent_id": "User",
        "evidence": compilation["evidence"],
        "timestamp": now.timestamp() as f64
    });
    let commits_dir = path.join(".vcs").join("commits");
    std::fs::create_dir_all(&commits_dir).map_err(|e| e.to_string())?;
    std::fs::write(
        commits_dir.join(format!("{}.json", commit_id)),
        serde_json::to_string_pretty(&commit).map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;

    Ok("Hypothesis integrated into main. Proposition statuses were not promoted.".to_string())
}

#[tauri::command]
pub fn get_vault_status(vault_path: String) -> Result<VaultStatus, String> {
    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }
    VcsWatcher::get_status(&path)
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
    VcsWatcher::get_territories(&path, branch.as_deref())
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
    VcsWatcher::get_knowledge_graph(&path, branch.as_deref())
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
        VcsWatcher::get_status(&path)?
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
        VcsWatcher::get_territories(&path, Some(&status.current_branch))?
    } else {
        vec![]
    };

    let context_summary = territories
        .iter()
        .map(|t| {
            format!(
                "- Territory [{}]: {}\n  Guide: {}\n  Findings: {}\n  Dead ends: {}\n  Hazards: {}\n  Propositions: {}",
                t.id,
                t.territory,
                t.guide,
                t.treasures.iter().map(|item| format!("{} ({})", item.description, item.rationale.as_deref().unwrap_or("no rationale recorded"))).collect::<Vec<_>>().join("; "),
                t.dead_ends.iter().map(|item| format!("{} ({})", item.description, item.rationale.as_deref().unwrap_or("no rationale recorded"))).collect::<Vec<_>>().join("; "),
                t.known_hazards.iter().map(|item| format!("{} ({})", item.description, item.rationale.as_deref().unwrap_or("no rationale recorded"))).collect::<Vec<_>>().join("; "),
                t.propositions.iter().map(|item| format!("{} [{}]; premises: {}; rationale: {}", item.claim, item.status, item.premises.join("; "), item.rationale.as_deref().unwrap_or("none recorded"))).collect::<Vec<_>>().join("; "),
            )
        })
        .collect::<Vec<_>>()
        .join("\n");

    let system_prompt = format!(
        "You are an AI Agent operating within the BeliefVCS framework.\n\
        Epistemic Principle: There are no facts, only beliefs given evidence. Knowledge is WIP always.\n\n\
        Current knowledge branch: {}\n\
        Knowledge available on this branch:\n{}\n\n\
        This chat is advisory: you cannot create branches, run probes, or merge knowledge here.\n\
        Do not claim to have tested or verified anything unless test evidence is provided.\n\
        Distinguish accepted claims, conjectures, counterevidence, assumptions, and uncertainty. Cite territory IDs when using repository knowledge.",
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
pub async fn assess_proposition(
    config: ModelConfig,
    vault_path: String,
    branch: String,
    claim: String,
    premises: Vec<String>,
    rationale: String,
) -> Result<ArgumentAssessment, String> {
    if claim.trim().is_empty() {
        return Err("A claim is required for assessment".to_string());
    }

    let path = resolve_vault_path(&vault_path);
    if !path.exists() {
        return Err(format!("Vault directory does not exist: {}", vault_path));
    }

    let main_territories = VcsWatcher::get_territories(&path, Some("main"))?;
    let branch_territories = if branch == "main" {
        Vec::new()
    } else {
        VcsWatcher::get_territories(&path, Some(&branch))?
    };
    let known_ids: std::collections::HashSet<String> =
        main_territories
            .iter()
            .chain(branch_territories.iter())
            .map(|territory| territory.id.clone())
            .collect();
    let context = serde_json::json!({
        "main_status_quo": main_territories,
        "active_hypothesis_branch": branch_territories,
    });

    let system_prompt = "Analyze the argument as a fallible natural-language reasoning aid. Do not decide that a claim is proven or true. Use only the supplied repository context; cite only its territory IDs. Return only JSON with this schema: {\"assessment\":\"SUPPORTS|CHALLENGES|MIXED|INSUFFICIENT\",\"reasoning\":\"...\",\"supporting_ids\":[],\"counterevidence_ids\":[],\"assumptions\":[],\"testable_predictions\":[]}. SUPPORTS requires supporting_ids; CHALLENGES requires counterevidence_ids; MIXED requires both. If the context is insufficient, use INSUFFICIENT. Keep testable_predictions falsifiable and scoped.";
    let user_content = serde_json::json!({
        "claim": claim,
        "premises": premises,
        "rationale": rationale,
        "repository_context": context,
    })
    .to_string();
    let messages = vec![
        ChatMessage {
            role: "system".to_string(),
            content: system_prompt.to_string(),
        },
        ChatMessage {
            role: "user".to_string(),
            content: user_content,
        },
    ];

    let raw = ModelClient::chat_completion(&config, &messages).await?;
    let trimmed = raw.trim();
    let json_str = if trimmed.starts_with("```") && trimmed.ends_with("```") {
        trimmed
            .lines()
            .skip(1)
            .take_while(|line| !line.trim_start().starts_with("```"))
            .collect::<Vec<_>>()
            .join("\n")
    } else {
        trimmed.to_string()
    };
    let assessment: ArgumentAssessment = serde_json::from_str(&json_str)
        .map_err(|e| format!("Model returned invalid argument-assessment JSON: {}", e))?;

    validate_argument_assessment(&assessment, &known_ids)?;

    Ok(assessment)
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
    yaml.push_str(&format!("id: {}\n", yaml_quote(&territory_id)?));
    yaml.push_str(&format!("territory: {}\n", yaml_quote(&input.territory)?));

    if !input.treasures.is_empty() {
        yaml.push_str("treasures:\n");
        for t in &input.treasures {
            yaml.push_str(&format!("- description: {}\n", yaml_quote(&t.description)?));
            if let Some(r) = &t.rationale {
                yaml.push_str(&format!("  rationale: {}\n", yaml_quote(r)?));
            } else {
                yaml.push_str("  rationale: null\n");
            }
        }
    }

    if !input.dead_ends.is_empty() {
        yaml.push_str("dead_ends:\n");
        for d in &input.dead_ends {
            yaml.push_str(&format!("- description: {}\n", yaml_quote(&d.description)?));
            if let Some(r) = &d.rationale {
                yaml.push_str(&format!("  rationale: {}\n", yaml_quote(r)?));
            } else {
                yaml.push_str("  rationale: null\n");
            }
        }
    }

    if !input.known_hazards.is_empty() {
        yaml.push_str("known_hazards:\n");
        for h in &input.known_hazards {
            yaml.push_str(&format!("- description: {}\n", yaml_quote(&h.description)?));
            if let Some(r) = &h.rationale {
                yaml.push_str(&format!("  rationale: {}\n", yaml_quote(r)?));
            } else {
                yaml.push_str("  rationale: null\n");
            }
        }
    }

    if !input.propositions.is_empty() {
        yaml.push_str("propositions:\n");
        for p in &input.propositions {
            let proposition_id = if p.id.trim().is_empty() {
                format!("{}-{}", territory_id, yaml.len())
            } else {
                p.id.trim().to_string()
            };
            yaml.push_str(&format!("- id: {}\n", yaml_quote(&proposition_id)?));
            yaml.push_str(&format!("  claim: {}\n", yaml_quote(&p.claim)?));
            if !p.premises.is_empty() {
                yaml.push_str("  premises:\n");
                for prem in &p.premises {
                    yaml.push_str(&format!("    - {}\n", yaml_quote(prem)?));
                }
            } else {
                yaml.push_str("  premises: []\n");
            }
            if let Some(r) = &p.rationale {
                yaml.push_str(&format!("  rationale: {}\n", yaml_quote(r)?));
            } else {
                yaml.push_str("  rationale: null\n");
            }
            yaml.push_str("  status: CONJECTURE\n");
        }
    }

    if !input.tags.is_empty() {
        yaml.push_str("tags:\n");
        for tag in &input.tags {
            yaml.push_str(&format!("- {}\n", yaml_quote(tag)?));
        }
    }

    if let Some(author) = &input.author_agent_id {
        yaml.push_str(&format!("author_agent_id: {}\n", yaml_quote(author)?));
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
  \"propositions\": [{\"claim\": \"Proposed claim\", \"premises\": [\"premise\"], \"rationale\": \"proposed reasoning\", \"status\": \"CONJECTURE\"}],\n\
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

    serde_json::from_str::<SaveTerritoryInput>(&json_str)
        .map_err(|e| format!("Failed to parse model distillation as the required schema: {}", e))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_vault_path(name: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "belief_{}_{}_{}",
            name,
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0)
        ))
    }

    fn test_territory_input(
        id: Option<&str>,
        territory: &str,
        guide: &str,
        propositions: Vec<PropositionItem>,
    ) -> SaveTerritoryInput {
        SaveTerritoryInput {
            id: id.map(str::to_string),
            territory: territory.to_string(),
            guide: guide.to_string(),
            treasures: vec![],
            dead_ends: vec![],
            known_hazards: vec![],
            propositions,
            tags: vec![],
            author_agent_id: Some("test".to_string()),
            branch: None,
            commit_message: None,
        }
    }

    #[test]
    fn test_argument_assessment_requires_valid_citations() {
        let known_ids = std::collections::HashSet::from(["territory-1".to_string()]);
        let unsupported = ArgumentAssessment {
            assessment: "SUPPORTS".to_string(),
            reasoning: "The evidence supports the claim.".to_string(),
            supporting_ids: vec!["invented-id".to_string()],
            counterevidence_ids: vec![],
            assumptions: vec![],
            testable_predictions: vec![],
        };
        assert!(validate_argument_assessment(&unsupported, &known_ids).is_err());

        let insufficient = ArgumentAssessment {
            assessment: "INSUFFICIENT".to_string(),
            reasoning: "The context does not decide the claim.".to_string(),
            supporting_ids: vec![],
            counterevidence_ids: vec![],
            assumptions: vec![],
            testable_predictions: vec![],
        };
        assert!(validate_argument_assessment(&insufficient, &known_ids).is_ok());
    }

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
            propositions: vec![PropositionItem {
                id: "prop-1".to_string(),
                claim: "A claim: with punctuation".to_string(),
                premises: vec!["A premise".to_string()],
                rationale: Some("A proposed rationale".to_string()),
                status: "PROVEN".to_string(),
            }],
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
        assert!(content.contains("territory: \"Rust Concurrency\""));
        assert!(content.contains("Mpsc channel"));
        assert!(content.contains("Blocking in async context"));
        assert!(content.contains("status: CONJECTURE"));
        let parsed = VcsWatcher::get_territories(&temp_dir, Some("main")).unwrap();
        assert_eq!(parsed[0].propositions[0].id, "prop-1");
        assert_eq!(parsed[0].propositions[0].status, "CONJECTURE");
        assert_eq!(parsed[0].propositions[0].premises, vec!["A premise".to_string()]);

        let _ = std::fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_hypothesis_branch_isolation_and_checkout() {
        let temp_dir = std::env::temp_dir().join(format!(
            "belief_branch_test_{}",
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0)
        ));
        std::fs::create_dir_all(&temp_dir).unwrap();
        std::fs::write(temp_dir.join("base.md"), "base knowledge").unwrap();

        let path = temp_dir.to_str().unwrap().to_string();
        assert_eq!(
            create_hypothesis_branch(path.clone(), "idea".to_string()).unwrap(),
            "hypothesis/idea"
        );
        std::fs::write(temp_dir.join("hypothesis.md"), "speculative knowledge").unwrap();

        checkout_branch(path.clone(), "main".to_string()).unwrap();
        assert!(temp_dir.join("base.md").exists());
        assert!(!temp_dir.join("hypothesis.md").exists());
        assert_eq!(
            VcsWatcher::get_current_branch(&temp_dir),
            "main"
        );

        checkout_branch(path, "hypothesis/idea".to_string()).unwrap();
        assert!(temp_dir.join("hypothesis.md").exists());
        assert_eq!(
            VcsWatcher::get_current_branch(&temp_dir),
            "hypothesis/idea"
        );
        std::fs::remove_dir_all(temp_dir).unwrap();
    }

    #[test]
    fn test_integrity_probe_and_merge_preserve_conjecture_status() {
        let vault = test_vault_path("desktop_probe_merge");
        std::fs::create_dir_all(&vault).unwrap();
        let vault_path = vault.to_string_lossy().to_string();

        save_territory(
            vault_path.clone(),
            test_territory_input(None, "Base", "Existing knowledge", vec![]),
        )
        .unwrap();
        let branch = create_hypothesis_branch(vault_path.clone(), "new-claim".to_string()).unwrap();
        save_territory(
            vault_path.clone(),
            test_territory_input(
                None,
                "Hypothesis",
                "A documented candidate claim",
                vec![PropositionItem {
                    id: "claim-1".to_string(),
                    claim: "A provisional claim".to_string(),
                    premises: vec!["A premise".to_string()],
                    rationale: None,
                    status: "PROVEN".to_string(),
                }],
            ),
        )
        .unwrap();

        let probe = run_knowledge_integrity_probe(vault_path.clone(), branch.clone()).unwrap();
        assert!(probe.passed);
        assert_eq!(probe.validation_profile.as_deref(), Some("knowledge-integrity-v1"));
        checkout_branch(vault_path.clone(), "main".to_string()).unwrap();
        let result = merge_hypothesis_to_main(vault_path.clone(), branch).unwrap();
        assert!(result.contains("statuses were not promoted"));

        let main = VcsWatcher::get_territories(&vault, Some("main")).unwrap();
        let claim = main
            .iter()
            .flat_map(|territory| territory.propositions.iter())
            .find(|proposition| proposition.id == "claim-1")
            .unwrap();
        assert_eq!(claim.status, "CONJECTURE");
        std::fs::remove_dir_all(vault).unwrap();
    }

    #[test]
    fn test_integrity_probe_rejects_stale_knowledge_snapshot() {
        let vault = test_vault_path("desktop_stale_probe");
        std::fs::create_dir_all(&vault).unwrap();
        let vault_path = vault.to_string_lossy().to_string();
        let branch = create_hypothesis_branch(vault_path.clone(), "stale".to_string()).unwrap();
        save_territory(
            vault_path.clone(),
            test_territory_input(None, "Before", "Before probe", vec![]),
        )
        .unwrap();
        assert!(run_knowledge_integrity_probe(vault_path.clone(), branch.clone())
            .unwrap()
            .passed);
        save_territory(
            vault_path.clone(),
            test_territory_input(None, "After", "Changed after probe", vec![]),
        )
        .unwrap();

        let error = merge_hypothesis_to_main(vault_path, branch).unwrap_err();
        assert!(error.contains("changed after its probe"));
        std::fs::remove_dir_all(vault).unwrap();
    }

    #[test]
    fn test_integrity_probe_fails_on_unresolved_knowledge_links() {
        let vault = test_vault_path("desktop_broken_link");
        std::fs::create_dir_all(&vault).unwrap();
        let vault_path = vault.to_string_lossy().to_string();
        let branch = create_hypothesis_branch(vault_path.clone(), "broken-link".to_string()).unwrap();
        save_territory(
            vault_path.clone(),
            test_territory_input(None, "Known", "See [[Missing Territory]].", vec![]),
        )
        .unwrap();

        let probe = run_knowledge_integrity_probe(vault_path.clone(), branch.clone()).unwrap();
        assert!(!probe.passed);
        assert!(probe.message.contains("links to missing territory"));
        assert!(merge_hypothesis_to_main(vault_path, branch).is_err());
        std::fs::remove_dir_all(vault).unwrap();
    }

    #[test]
    fn test_integrity_probe_merge_rejects_conflicting_main_edit() {
        let vault = test_vault_path("desktop_merge_conflict");
        std::fs::create_dir_all(&vault).unwrap();
        let vault_path = vault.to_string_lossy().to_string();
        let id = save_territory(
            vault_path.clone(),
            test_territory_input(None, "Shared", "Original", vec![]),
        )
        .unwrap();
        let branch = create_hypothesis_branch(vault_path.clone(), "conflict".to_string()).unwrap();
        save_territory(
            vault_path.clone(),
            test_territory_input(Some(&id), "Shared", "Hypothesis edit", vec![]),
        )
        .unwrap();
        assert!(run_knowledge_integrity_probe(vault_path.clone(), branch.clone())
            .unwrap()
            .passed);
        checkout_branch(vault_path.clone(), "main".to_string()).unwrap();
        save_territory(
            vault_path.clone(),
            test_territory_input(Some(&id), "Shared", "Independent main edit", vec![]),
        )
        .unwrap();

        let error = merge_hypothesis_to_main(vault_path.clone(), branch).unwrap_err();
        assert!(error.contains("both branches changed the same records"));
        let main = VcsWatcher::get_territories(&vault, Some("main")).unwrap();
        assert_eq!(main[0].guide, "Independent main edit");
        std::fs::remove_dir_all(vault).unwrap();
    }
}
