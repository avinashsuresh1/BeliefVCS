pub mod commands;
pub mod model_client;
pub mod vcs_watcher;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            commands::get_vault_status,
            commands::list_branches,
            commands::get_territories,
            commands::get_commit_history,
            commands::get_compilations,
            commands::get_knowledge_graph,
            commands::test_model_connection,
            commands::send_agent_prompt
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
