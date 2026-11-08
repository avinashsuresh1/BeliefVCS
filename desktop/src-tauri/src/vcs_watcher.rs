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
    pub exit_code: i32,
    pub proof_sound: Option<bool>,
    pub proof_violations: Vec<String>,
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
    pub fn get_status(vault_path: &Path) -> VaultStatus {
        let current_branch = Self::get_current_branch(vault_path);
        let branches = Self::list_branches(vault_path);

        let territories = Self::get_territories(vault_path, Some(&current_branch));
        let commits = Self::get_commits(vault_path);
        let compilations = Self::get_compilations(vault_path);

        VaultStatus {
            current_branch,
            branches,
            total_territories: territories.len(),
            total_commits: commits.len(),
            total_compilations: compilations.len(),
        }
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
    pub fn get_territories(vault_path: &Path, branch: Option<&str>) -> Vec<TerritoryCard> {
        let target_dir: PathBuf = match branch {
            Some(b) if b != "main" => {
                if let Some(sanitized) = Self::sanitize_branch_name(b) {
                    let b_dir = vault_path.join(".vcs").join("branches").join(sanitized);
                    if b_dir.exists() {
                        b_dir
                    } else {
                        vault_path.to_path_buf()
                    }
                } else {
                    vault_path.to_path_buf()
                }
            }
            _ => vault_path.to_path_buf(),
        };

        let mut territories = Vec::new();
        if !target_dir.exists() {
            return territories;
        }

        let link_re = Regex::new(r"\[\[(.*?)\]\]").unwrap();

        if let Ok(entries) = fs::read_dir(target_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().map(|e| e == "md").unwrap_or(false) {
                    if let Ok(content) = fs::read_to_string(&path) {
                        if let Some(card) = Self::parse_markdown_territory(&content, &link_re) {
                            territories.push(card);
                        }
                    }
                }
            }
        }

        territories
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
        let mut propositions = Vec::new();

        let mut current_section = "";

        for line in yaml_str.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("id:") {
                id = trimmed.trim_start_matches("id:").trim().to_string();
                current_section = "";
            } else if trimmed.starts_with("territory:") {
                territory = trimmed.trim_start_matches("territory:").trim().to_string();
                current_section = "";
            } else if trimmed.starts_with("author_agent_id:") {
                author_agent_id = Some(trimmed.trim_start_matches("author_agent_id:").trim().to_string());
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
                if item.starts_with("description:") {
                    item = item.trim_start_matches("description:").trim().to_string();
                } else if item.starts_with("claim:") {
                    item = item.trim_start_matches("claim:").trim().to_string();
                }

                match current_section {
                    "tags" => tags.push(item),
                    "treasures" => treasures.push(ObservationItem {
                        description: item,
                        rationale: None,
                    }),
                    "dead_ends" => dead_ends.push(ObservationItem {
                        description: item,
                        rationale: None,
                    }),
                    "known_hazards" => known_hazards.push(ObservationItem {
                        description: item,
                        rationale: None,
                    }),
                    "propositions" => propositions.push(PropositionItem {
                        claim: item,
                        premises: vec![],
                        rationale: None,
                        status: "PROVEN".to_string(),
                    }),
                    _ => {}
                }
            } else if trimmed.starts_with("description:") {
                let desc = trimmed.trim_start_matches("description:").trim().to_string();
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
                let claim = trimmed.trim_start_matches("claim:").trim().to_string();
                propositions.push(PropositionItem {
                    claim,
                    premises: vec![],
                    rationale: None,
                    status: "PROVEN".to_string(),
                });
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
                                last.rationale = Some(rat);
                            }
                        }
                        _ => {}
                    }
                }
            }
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

                                let proof_sound = val["proof_verification"]["sound"].as_bool();
                                let mut violations = Vec::new();
                                if let Some(arr) = val["proof_verification"]["violations"].as_array() {
                                    for v in arr {
                                        if let Some(s) = v.as_str() {
                                            violations.push(s.to_string());
                                        }
                                    }
                                }

                                compilations.push(CompilationItem {
                                    branch: branch_name,
                                    passed,
                                    message,
                                    test_command,
                                    exit_code,
                                    proof_sound,
                                    proof_violations: violations,
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
    pub fn get_knowledge_graph(vault_path: &Path, branch: Option<&str>) -> GraphData {
        let territories = Self::get_territories(vault_path, branch);
        let mut nodes = Vec::new();
        let mut edges = Vec::new();

        let territory_names: Vec<String> = territories.iter().map(|t| t.territory.to_lowercase()).collect();

        for t in &territories {
            nodes.push(GraphNode {
                id: t.territory.clone(),
                label: t.territory.clone(),
                group: if t.propositions.is_empty() { "territory".to_string() } else { "axiom".to_string() },
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

        GraphData { nodes, edges }
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
}
