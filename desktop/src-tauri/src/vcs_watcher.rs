use regex::Regex;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultStatus {
    pub current_branch: String,
    pub branches: Vec<String>,
    pub total_territories: usize,
    pub total_commits: usize,
    pub total_compilations: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObservationItem {
    pub description: String,
    pub rationale: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PropositionItem {
    #[serde(default)]
    pub id: String,
    pub claim: String,
    pub premises: Vec<String>,
    pub rationale: Option<String>,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TerritoryCard {
    pub id: String,
    pub territory: String,
    pub guide: String,
    pub treasures: Vec<ObservationItem>,
    pub dead_ends: Vec<ObservationItem>,
    pub known_hazards: Vec<ObservationItem>,
    pub propositions: Vec<PropositionItem>,
    pub tags: Vec<String>,
    pub author_agent_id: Option<String>,
    pub wiki_links: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommitItem {
    pub id: String,
    pub branch: String,
    pub message: String,
    pub author_agent_id: Option<String>,
    pub timestamp: f64,
    pub has_evidence: bool,
    pub evidence_exit_code: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompilationItem {
    pub branch: String,
    pub passed: bool,
    pub message: String,
    pub test_command: String,
    pub validation_profile: Option<String>,
    pub revision_digest: Option<String>,
    pub exit_code: i32,
    pub proof_sound: Option<bool>,
    pub proof_verdict: Option<String>,
    pub proof_violations: Vec<String>,
    pub candidate_conflicts: Vec<String>,
    pub supporting_ids: Vec<String>,
    pub counterevidence_ids: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphNode {
    pub id: String,
    pub label: String,
    pub group: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphEdge {
    pub source: String,
    pub target: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphData {
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
}

pub struct VcsWatcher;

impl VcsWatcher {
    fn parse_scalar(value: &str) -> String {
        let trimmed = value.trim();
        if trimmed.starts_with('"') {
            serde_json::from_str::<String>(trimmed).unwrap_or_else(|_| trimmed.to_string())
        } else if trimmed.len() >= 2 && trimmed.starts_with('\'') && trimmed.ends_with('\'') {
            trimmed[1..trimmed.len() - 1].replace("''", "'")
        } else {
            trimmed.to_string()
        }
    }

    /// Read HEAD to find active branch name
    pub fn get_current_branch(vault_path: &Path) -> String {
        let head_path = vault_path.join(".vcs").join("HEAD");
        if head_path.exists() {
            fs::read_to_string(&head_path)
                .map(|s| s.trim().to_string())
                .unwrap_or_else(|_| "main".to_string())
        } else {
            "main".to_string()
        }
    }

    /// List all knowledge branches
    pub fn list_branches(vault_path: &Path) -> Vec<String> {
        let branches_dir = vault_path.join(".vcs").join("branches");
        let mut branches = vec!["main".to_string()];
        if branches_dir.exists() {
            if let Ok(entries) = fs::read_dir(branches_dir) {
                for entry in entries.flatten() {
                    if let Ok(file_type) = entry.file_type() {
                        if file_type.is_dir() {
                            let name = entry.file_name().to_string_lossy().replace("__", "/");
                            if !branches.contains(&name) {
                                branches.push(name);
                            }
                        }
                    }
                }
            }
        }
        branches
    }

    /// Read comprehensive vault status
    pub fn get_status(vault_path: &Path) -> Result<VaultStatus, String> {
        let current_branch = Self::get_current_branch(vault_path);
        let branches = Self::list_branches(vault_path);

        let territories = Self::get_territories(vault_path, Some(&current_branch))?;
        let commits = Self::get_commits(vault_path);
        let compilations = Self::get_compilations(vault_path);

        Ok(VaultStatus {
            current_branch,
            branches,
            total_territories: territories.len(),
            total_commits: commits.len(),
            total_compilations: compilations.len(),
        })
    }

    /// Sanitize branch name preventing path traversal
    pub fn sanitize_branch_name(name: &str) -> Option<String> {
        let trimmed = name.trim();
        if trimmed.is_empty() || trimmed.contains("..") || trimmed.contains(':') {
            return None;
        }
        Some(trimmed.replace('/', "__").replace('\\', "__"))
    }

    /// Parse markdown files from working tree or specific branch
    pub fn get_territories(vault_path: &Path, branch: Option<&str>) -> Result<Vec<TerritoryCard>, String> {
        let target_dir: PathBuf = match branch {
            Some(b) => {
                let sanitized = Self::sanitize_branch_name(b)
                    .ok_or_else(|| format!("Invalid branch name: {}", b))?;
                let branches_dir = vault_path.join(".vcs").join("branches");
                let branch_dir = branches_dir.join(sanitized);
                if branch_dir.exists() {
                    branch_dir
                } else if branches_dir.exists() {
                    return Err(format!("Branch '{}' does not exist in this vault", b));
                } else {
                    vault_path.to_path_buf()
                }
            }
            None => vault_path.to_path_buf(),
        };

        let mut territories = Vec::new();
        if !target_dir.exists() {
            return Ok(territories);
        }

        let link_re = Regex::new(r"\[\[(.*?)\]\]").unwrap();

        let entries = fs::read_dir(&target_dir).map_err(|e| {
            format!("Failed to read knowledge directory {}: {}", target_dir.display(), e)
        })?;
        for entry in entries {
            let entry = entry.map_err(|e| format!("Failed to read knowledge entry: {}", e))?;
            let path = entry.path();
            if path.extension().map(|e| e == "md").unwrap_or(false) {
                let content = fs::read_to_string(&path).map_err(|e| {
                    format!("Failed to read knowledge file {}: {}", path.display(), e)
                })?;
                let card = Self::parse_markdown_territory(&content, &link_re)
                    .ok_or_else(|| format!("Malformed knowledge file: {}", path.display()))?;
                territories.push(card);
            }
        }

        Ok(territories)
    }

    fn parse_markdown_territory(content: &str, link_re: &Regex) -> Option<TerritoryCard> {
        let parts: Vec<&str> = content.splitn(3, "---").collect();
        if parts.len() < 3 {
            return None;
        }

        let yaml_str = parts[1];
        let body = parts[2];

        let guide = if let Some(idx) = body.find("# Guide") {
            body[idx + 7..].trim().to_string()
        } else {
            body.trim().to_string()
        };

        let mut wiki_links = Vec::new();
        for cap in link_re.captures_iter(content) {
            if let Some(m) = cap.get(1) {
                wiki_links.push(m.as_str().to_string());
            }
        }

        let mut id = String::new();
        let mut territory = String::new();
        let mut author_agent_id = None;
        let mut tags = Vec::new();
        let mut treasures = Vec::new();
        let mut dead_ends = Vec::new();
        let mut known_hazards = Vec::new();
        let mut propositions: Vec<PropositionItem> = Vec::new();

        let mut current_section = "";

        for line in yaml_str.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("id:") && current_section == "propositions" {
                if let Some(proposition) = propositions.last_mut() {
                    proposition.id = Self::parse_scalar(trimmed.trim_start_matches("id:"));
                }
            } else if line.starts_with("id:") {
                id = Self::parse_scalar(trimmed.trim_start_matches("id:"));
                current_section = "";
            } else if line.starts_with("territory:") {
                territory = Self::parse_scalar(trimmed.trim_start_matches("territory:"));
                current_section = "";
            } else if line.starts_with("author_agent_id:") {
                author_agent_id = Some(Self::parse_scalar(trimmed.trim_start_matches("author_agent_id:")));
                current_section = "";
            } else if trimmed.starts_with("treasures:") {
                current_section = "treasures";
            } else if trimmed.starts_with("dead_ends:") {
                current_section = "dead_ends";
            } else if trimmed.starts_with("known_hazards:") {
                current_section = "known_hazards";
            } else if trimmed.starts_with("propositions:") {
                current_section = "propositions";
            } else if trimmed.starts_with("tags:") {
                current_section = "tags";
            } else if trimmed.starts_with("- ") {
                let mut item = trimmed.trim_start_matches("- ").trim().to_string();
                if current_section == "propositions" && item.starts_with("id:") {
                    propositions.push(PropositionItem {
                        id: Self::parse_scalar(item.trim_start_matches("id:")),
                        claim: String::new(),
                        premises: vec![],
                        rationale: None,
                        status: "CONJECTURE".to_string(),
                    });
                    continue;
                }
                if current_section != "propositions" && item.starts_with("id:") {
                    continue;
                }
                if item.starts_with("description:") {
                    item = item.trim_start_matches("description:").trim().to_string();
                } else if item.starts_with("claim:") {
                    item = item.trim_start_matches("claim:").trim().to_string();
                }

                match current_section {
                    "tags" => tags.push(Self::parse_scalar(&item)),
                    "treasures" => treasures.push(ObservationItem {
                        description: Self::parse_scalar(&item),
                        rationale: None,
                    }),
                    "dead_ends" => dead_ends.push(ObservationItem {
                        description: Self::parse_scalar(&item),
                        rationale: None,
                    }),
                    "known_hazards" => known_hazards.push(ObservationItem {
                        description: Self::parse_scalar(&item),
                        rationale: None,
                    }),
                    "propositions" => propositions.push(PropositionItem {
                        id: String::new(),
                        claim: Self::parse_scalar(&item),
                        premises: vec![],
                        rationale: None,
                        status: "CONJECTURE".to_string(),
                    }),
                    "proposition_premises" => {
                        if let Some(proposition) = propositions.last_mut() {
                            proposition.premises.push(Self::parse_scalar(&item));
                        }
                    }
                    _ => {}
                }
            } else if trimmed.starts_with("description:") {
                let desc = Self::parse_scalar(trimmed.trim_start_matches("description:"));
                match current_section {
                    "treasures" => {
                        treasures.push(ObservationItem {
                            description: desc,
                            rationale: None,
                        });
                    }
                    "dead_ends" => {
                        dead_ends.push(ObservationItem {
                            description: desc,
                            rationale: None,
                        });
                    }
                    "known_hazards" => {
                        known_hazards.push(ObservationItem {
                            description: desc,
                            rationale: None,
                        });
                    }
                    _ => {}
                }
            } else if trimmed.starts_with("claim:") {
                let claim = Self::parse_scalar(trimmed.trim_start_matches("claim:"));
                if let Some(proposition) = propositions.last_mut() {
                    proposition.claim = claim;
                } else {
                    propositions.push(PropositionItem {
                        id: String::new(),
                        claim,
                        premises: vec![],
                        rationale: None,
                        status: "CONJECTURE".to_string(),
                    });
                }
                current_section = "propositions";
            } else if trimmed.starts_with("premises:") && current_section == "propositions" {
                current_section = "proposition_premises";
            } else if trimmed.starts_with("status:")
                && (current_section == "propositions" || current_section == "proposition_premises")
            {
                if let Some(proposition) = propositions.last_mut() {
                    let status = Self::parse_scalar(trimmed.trim_start_matches("status:"));
                    proposition.status = if status == "PROVEN" {
                        "LEGACY_PROVEN".to_string()
                    } else {
                        status
                    };
                }
                current_section = "propositions";
            } else if trimmed.starts_with("rationale:") {
                let rat = trimmed.trim_start_matches("rationale:").trim().to_string();
                if rat != "null" && !rat.is_empty() {
                    match current_section {
                        "treasures" => {
                            if let Some(last) = treasures.last_mut() {
                                last.rationale = Some(rat);
                            }
                        }
                        "dead_ends" => {
                            if let Some(last) = dead_ends.last_mut() {
                                last.rationale = Some(rat);
                            }
                        }
                        "known_hazards" => {
                            if let Some(last) = known_hazards.last_mut() {
                                last.rationale = Some(Self::parse_scalar(&rat));
                            }
                        }
                        "propositions" | "proposition_premises" => {
                            if let Some(last) = propositions.last_mut() {
                                last.rationale = Some(Self::parse_scalar(&rat));
                            }
                        }
                        _ => {}
                    }
                }
                if current_section == "proposition_premises" {
                    current_section = "propositions";
                }
            }
        }

        if territory.trim().is_empty() {
            return None;
        }
        if id.is_empty() {
            id = territory.clone();
        }

        Some(TerritoryCard {
            id,
            territory,
            guide,
            treasures,
            dead_ends,
            known_hazards,
            propositions,
            tags,
            author_agent_id,
            wiki_links,
        })
    }

    /// Read belief commits from .vcs/commits/
    pub fn get_commits(vault_path: &Path) -> Vec<CommitItem> {
        let commits_dir = vault_path.join(".vcs").join("commits");
        let mut commits = Vec::new();

        if commits_dir.exists() {
            if let Ok(entries) = fs::read_dir(commits_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().map(|e| e == "json").unwrap_or(false) {
                        if let Ok(content) = fs::read_to_string(&path) {
                            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                                let id = val["id"].as_str().unwrap_or("").to_string();
                                let branch = val["branch"].as_str().unwrap_or("main").to_string();
                                let message = val["message"].as_str().unwrap_or("").to_string();
                                let author = val["author_agent_id"].as_str().map(|s| s.to_string());
                                let timestamp = val["timestamp"].as_f64().unwrap_or(0.0);
                                let has_evidence = !val["evidence"].is_null();
                                let exit_code = val["evidence"]["exit_code"].as_i64().map(|c| c as i32);

                                commits.push(CommitItem {
                                    id,
                                    branch,
                                    message,
                                    author_agent_id: author,
                                    timestamp,
                                    has_evidence,
                                    evidence_exit_code: exit_code,
                                });
                            }
                        }
                    }
                }
            }
        }

        commits.sort_by(|a, b| b.timestamp.partial_cmp(&a.timestamp).unwrap_or(std::cmp::Ordering::Equal));
        commits
    }

    /// Read compilation results from .vcs/compilations/
    pub fn get_compilations(vault_path: &Path) -> Vec<CompilationItem> {
        let comp_dir = vault_path.join(".vcs").join("compilations");
        let mut compilations = Vec::new();

        if comp_dir.exists() {
            if let Ok(entries) = fs::read_dir(comp_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().map(|e| e == "json").unwrap_or(false) {
                        let branch_name = path
                            .file_stem()
                            .map(|s| s.to_string_lossy().replace("__", "/"))
                            .unwrap_or_else(|| "unknown".to_string());

                        if let Ok(content) = fs::read_to_string(&path) {
                            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                                let passed = val["passed"].as_bool().unwrap_or(false);
                                let message = val["message"].as_str().unwrap_or("").to_string();
                                let test_command = val["evidence"]["test_command"].as_str().unwrap_or("").to_string();
                                let exit_code = val["evidence"]["exit_code"].as_i64().unwrap_or(-1) as i32;
                                let validation_profile = val["validation_profile"]
                                    .as_str()
                                    .map(|s| s.to_string());
                                let revision_digest = val["revision_digest"]
                                    .as_str()
                                    .map(|s| s.to_string());

                                let proof_sound = val["proof_verification"]["sound"].as_bool();
                                let proof_verdict = val["proof_verification"]["verdict"]
                                    .as_str()
                                    .map(|s| s.to_string());
                                let mut violations = Vec::new();
                                let mut candidate_conflicts = Vec::new();
                                let mut supporting_ids = Vec::new();
                                let mut counterevidence_ids = Vec::new();
                                if let Some(arr) = val["proof_verification"]["violations"].as_array() {
                                    for v in arr {
                                        if let Some(s) = v.as_str() {
                                            violations.push(s.to_string());
                                        }
                                    }
                                }
                                for (key, values) in [
                                    ("candidate_conflicts", &mut candidate_conflicts),
                                    ("supporting_ids", &mut supporting_ids),
                                    ("counterevidence_ids", &mut counterevidence_ids),
                                ] {
                                    if let Some(arr) = val["proof_verification"][key].as_array() {
                                        values.extend(
                                            arr.iter().filter_map(|value| {
                                                value.as_str().map(|s| s.to_string())
                                            }),
                                        );
                                    }
                                }

                                compilations.push(CompilationItem {
                                    branch: branch_name,
                                    passed,
                                    message,
                                    test_command,
                                    validation_profile,
                                    revision_digest,
                                    exit_code,
                                    proof_sound,
                                    proof_verdict,
                                    proof_violations: violations,
                                    candidate_conflicts,
                                    supporting_ids,
                                    counterevidence_ids,
                                });
                            }
                        }
                    }
                }
            }
        }

        compilations
    }

    /// Build topological network graph of territories and wiki-links
    pub fn get_knowledge_graph(vault_path: &Path, branch: Option<&str>) -> Result<GraphData, String> {
        let territories = Self::get_territories(vault_path, branch)?;
        let mut nodes = Vec::new();
        let mut edges = Vec::new();

        let territory_names: Vec<String> = territories.iter().map(|t| t.territory.to_lowercase()).collect();

        for t in &territories {
            nodes.push(GraphNode {
                id: t.territory.clone(),
                label: t.territory.clone(),
                group: if t.propositions.is_empty() { "territory".to_string() } else { "proposition".to_string() },
            });

            for link in &t.wiki_links {
                let link_clean = link.trim().to_lowercase();
                if territory_names.contains(&link_clean) {
                    let target_name = territories
                        .iter()
                        .find(|x| x.territory.to_lowercase() == link_clean)
                        .map(|x| x.territory.clone())
                        .unwrap_or_else(|| link.clone());

                    edges.push(GraphEdge {
                        source: t.territory.clone(),
                        target: target_name,
                    });
                }
            }
        }

        Ok(GraphData { nodes, edges })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_markdown_territory() {
        let raw = r#"---
id: test-123
territory: Web Scraping
treasures:
- description: BeautifulSoup is fast
  rationale: C parser
dead_ends:
- description: Used Regex
  rationale: Fails on HTML
tags:
- python
- web
---

# Guide
Use [[Playwright]] for SPAs.
"#;
        let link_re = Regex::new(r"\[\[(.*?)\]\]").unwrap();
        let card = VcsWatcher::parse_markdown_territory(raw, &link_re).expect("Should parse");
        assert_eq!(card.territory, "Web Scraping");
        assert_eq!(card.guide, "Use [[Playwright]] for SPAs.");
        assert_eq!(card.wiki_links, vec!["Playwright".to_string()]);
        assert_eq!(card.treasures.len(), 1);
        assert_eq!(card.treasures[0].description, "BeautifulSoup is fast");
        assert_eq!(card.treasures[0].rationale, Some("C parser".to_string()));
        assert_eq!(card.dead_ends.len(), 1);
        assert_eq!(card.dead_ends[0].description, "Used Regex");
    }

    #[test]
    fn test_parse_proposition_keeps_id_and_status() {
        let raw = r#"---
id: territory-1
territory: Claims
treasures:
- id: observation-1
  description: "A supporting observation."
propositions:
- id: proposition-1
  claim: "A scoped claim."
  premises:
    - "A cited premise."
  rationale: "Proposed reasoning."
  status: CONJECTURE
---
# Guide
Review the claim.
"#;
        let link_re = Regex::new(r"\[\[(.*?)\]\]").unwrap();
        let card = VcsWatcher::parse_markdown_territory(raw, &link_re).unwrap();
        assert_eq!(card.id, "territory-1");
        assert_eq!(card.treasures.len(), 1);
        assert_eq!(card.treasures[0].description, "A supporting observation.");
        assert_eq!(card.propositions.len(), 1);
        assert_eq!(card.propositions[0].id, "proposition-1");
        assert_eq!(card.propositions[0].claim, "A scoped claim.");
        assert_eq!(card.propositions[0].premises, vec!["A cited premise.".to_string()]);
        assert_eq!(card.propositions[0].status, "CONJECTURE");
    }

    #[test]
    fn test_knowledge_graph_linking() {
        let raw1 = r#"---
id: 1
territory: A
---
# Guide
Connects to [[B]].
"#;
        let raw2 = r#"---
id: 2
territory: B
---
# Guide
Destination node.
"#;
        let link_re = Regex::new(r"\[\[(.*?)\]\]").unwrap();
        let card1 = VcsWatcher::parse_markdown_territory(raw1, &link_re).unwrap();
        let card2 = VcsWatcher::parse_markdown_territory(raw2, &link_re).unwrap();

        let territories = vec![card1, card2];
        let territory_names: Vec<String> = territories.iter().map(|t| t.territory.to_lowercase()).collect();

        let mut edges = Vec::new();
        for t in &territories {
            for link in &t.wiki_links {
                if territory_names.contains(&link.to_lowercase()) {
                    edges.push(GraphEdge {
                        source: t.territory.clone(),
                        target: link.clone(),
                    });
                }
            }
        }

        assert_eq!(edges.len(), 1);
        assert_eq!(edges[0].source, "A");
        assert_eq!(edges[0].target, "B");
    }

    #[test]
    fn test_sanitize_branch_name() {
        assert_eq!(
            VcsWatcher::sanitize_branch_name("hypothesis/my-feature"),
            Some("hypothesis__my-feature".to_string())
        );
        assert_eq!(
            VcsWatcher::sanitize_branch_name("hypothesis\\win-path"),
            Some("hypothesis__win-path".to_string())
        );
        assert_eq!(VcsWatcher::sanitize_branch_name("../traversal"), None);
        assert_eq!(VcsWatcher::sanitize_branch_name("foo/../../bar"), None);
        assert_eq!(VcsWatcher::sanitize_branch_name("c:secret"), None);
        assert_eq!(VcsWatcher::sanitize_branch_name("   "), None);
    }

    #[test]
    fn test_territory_read_surfaces_malformed_markdown() {
        let vault = std::env::temp_dir().join(format!(
            "belief_malformed_vault_{}",
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0)
        ));
        let main_dir = vault.join(".vcs").join("branches").join("main");
        std::fs::create_dir_all(&main_dir).unwrap();
        std::fs::write(main_dir.join("broken.md"), "not valid frontmatter").unwrap();

        let error = VcsWatcher::get_territories(&vault, Some("main")).unwrap_err();
        assert!(error.contains("Malformed knowledge file"));

        std::fs::remove_dir_all(vault).unwrap();
    }
}
