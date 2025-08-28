import SwiftUI

@main
struct FTGCompanionApp: App {
    var body: some Scene {
        WindowGroup {
            MainView()
        }.windowStyle(.automatic)
    }
}

struct MainView: View {
    @AppStorage("AppLang") private var appLang: String = Locale.current.language.languageCode?.identifier == "ru" ? "ru" : "en"
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text(appLang == "ru" ? "Язык:" : "Language:")
                Picker("", selection: $appLang) {
                    Text("RU").tag("ru")
                    Text("EN").tag("en")
                }.pickerStyle(.segmented)
                Spacer()
            }.padding([.leading, .trailing, .top], 8)
            TabView {
                DashboardView(appLang: appLang)
                    .tabItem { Label(appLang == "ru" ? "Панель" : "Dashboard", systemImage: "speedometer") }

                AISettingsView(appLang: appLang)
                    .tabItem { Label(appLang == "ru" ? "ИИ" : "AI Settings", systemImage: "brain.head.profile") }

                WebPanelContainer()
                    .tabItem { Label(appLang == "ru" ? "Веб" : "Web Panel", systemImage: "globe") }

                LogsView(appLang: appLang)
                    .tabItem { Label(appLang == "ru" ? "Логи" : "Logs", systemImage: "doc.text.magnifyingglass") }

                ShortcutsView(appLang: appLang)
                    .tabItem { Label(appLang == "ru" ? "Ярлыки" : "Shortcuts", systemImage: "bolt.fill") }

                MessagesView(appLang: appLang)
                    .tabItem { Label(appLang == "ru" ? "Сообщения" : "Messages", systemImage: "paperplane.fill") }

                ServerSettingsView(appLang: appLang)
                    .tabItem { Label(appLang == "ru" ? "Сервер" : "Server", systemImage: "lock.shield") }

                BotSettingsView(appLang: appLang)
                    .tabItem { Label(appLang == "ru" ? "Бот" : "Bot Settings", systemImage: "gearshape") }
            }
            .frame(minWidth: 900, minHeight: 600)
        }
    }
}

final class ControlClient {
    static let shared = ControlClient()
    private init() {}

    private let baseURL = URL(string: "http://127.0.0.1:8787")!
    private var token: String { Keychain.get("FTGControlToken") ?? UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token" }

    func getHealth() async throws -> (status: String, ftg: String) {
        var req = URLRequest(url: baseURL.appendingPathComponent("/health"))
        req.addValue(token, forHTTPHeaderField: "X-FTG-Token")
        let (data, resp) = try await URLSession.shared.data(for: req)
        guard let http = resp as? HTTPURLResponse, http.statusCode == 200 else { throw URLError(.badServerResponse) }
        let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let status = obj?["status"] as? String ?? ""
        let ftg = obj?["ftg"] as? String ?? ""
        return (status, ftg)
    }
}

struct DashboardView: View {
    let appLang: String
    @State private var status: String = "unknown"
    @State private var ftg: String = "unknown"
    @State private var loading = false
    @State private var ftgRunning = false
    @State private var actionInProgress = false
    @State private var lastActionMessage: String = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text((appLang == "ru" ? "Статус: " : "Status: ")) + Text(status).bold()
                Text((appLang == "ru" ? "FTG: " : "FTG: ")) + Text(ftg).bold()
                Spacer()
                Button(loading ? (appLang == "ru" ? "Загрузка…" : "Loading…") : (appLang == "ru" ? "Обновить" : "Refresh")) { Task { await refresh() } }
                    .disabled(loading)
            }
            HStack(spacing: 12) {
                Button(actionInProgress ? (appLang == "ru" ? "Запуск…" : "Starting…") : (appLang == "ru" ? "Запустить" : "Start")) { Task { await execAction("start") } }
                    .disabled(ftgRunning || actionInProgress)
                Button(actionInProgress ? (appLang == "ru" ? "Остановка…" : "Stopping…") : (appLang == "ru" ? "Остановить" : "Stop")) { Task { await execAction("stop") } }
                    .disabled(!ftgRunning || actionInProgress)
                Button(actionInProgress ? (appLang == "ru" ? "Перезапуск…" : "Restarting…") : (appLang == "ru" ? "Перезапуск" : "Restart")) { Task { await execAction("restart") } }
                    .disabled(actionInProgress)
                Button(appLang == "ru" ? "Статус" : "Status") { Task { await execAction("status") } }
            }
            Divider()
            if actionInProgress { ProgressView().controlSize(.small) }
            if !lastActionMessage.isEmpty { Text(lastActionMessage).font(.caption).foregroundStyle(.secondary) }
            Spacer()
        }
        .padding()
        .task { await loop() }
    }

    private func refresh() async {
        loading = true
        defer { loading = false }
        do {
            let res = try await ControlClient.shared.getHealth()
            status = res.status
            ftg = res.ftg
            // probe status via /exec
            if let url = URL(string: "http://127.0.0.1:8787/exec"),
               let token = UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token" as String? {
                var req = URLRequest(url: url)
                req.httpMethod = "POST"
                req.addValue(Keychain.get("FTGControlToken") ?? token, forHTTPHeaderField: "X-FTG-Token")
                req.addValue("application/json", forHTTPHeaderField: "Content-Type")
                req.httpBody = try? JSONSerialization.data(withJSONObject: ["action":"status"]) 
                let (data, _) = try await URLSession.shared.data(for: req)
                if let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    self.ftgRunning = (obj["running"] as? Bool) ?? false
                }
            }
        } catch {
            status = "error"
            ftg = "unknown"
        }
    }

    private func execAction(_ action: String) async {
        guard let url = URL(string: "http://127.0.0.1:8787/exec") else { return }
        actionInProgress = true
        defer { actionInProgress = false }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.addValue(Keychain.get("FTGControlToken") ?? UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token", forHTTPHeaderField: "X-FTG-Token")
        req.addValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["action": action])
        req.timeoutInterval = 8
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            if let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any], let ok = obj["ok"] as? Bool {
                lastActionMessage = ok ? "Action \(action) OK" : (obj["error"] as? String ?? "Action failed")
            } else { lastActionMessage = "Action \(action) sent" }
            await refresh()
        } catch {
            lastActionMessage = "Action \(action) error: \(error.localizedDescription)"
        }
    }

    private func loop() async {
        while true {
            await refresh()
            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }
    }
}

struct AISettingsView: View {
    let appLang: String
    @State private var providers: [[String: Any]] = []
    @State private var selectedBaseURL: String = "http://127.0.0.1:1234/v1"
    @State private var model: String = "gpt-oss:latest"
    @State private var apiKey: String = (Keychain.get("LLM_API_KEY") ?? "")
    @State private var timeout: String = "60"
    @State private var prompt = "Hello"
    @State private var output = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Button(appLang == "ru" ? "Загрузить провайдеры" : "Load Providers") { Task { await loadProviders() } }
                Button(appLang == "ru" ? "Применить конфигурацию" : "Apply Config") { Task { await applyConfig() } }
                Button(appLang == "ru" ? "Сохранить ключ" : "Save Key") { _ = Keychain.set(apiKey, for: "LLM_API_KEY") }
            }
            TextField(appLang == "ru" ? "Базовый URL" : "Base URL", text: $selectedBaseURL)
            TextField(appLang == "ru" ? "Модель" : "Model", text: $model)
            SecureField(appLang == "ru" ? "API Ключ (опционально)" : "API Key (optional)", text: $apiKey)
            TextField(appLang == "ru" ? "Время ожидания запроса (сек)" : "Request timeout seconds", text: $timeout)
            TextField(appLang == "ru" ? "Тестовый запрос" : "Test prompt", text: $prompt)
            HStack {
                Button(appLang == "ru" ? "Тест /llm/chat" : "Test /llm/chat") { Task { await runTest() } }
            }
            ScrollView { Text(output).frame(maxWidth: .infinity, alignment: .leading) }
            Spacer()
        }.padding()
    }

    private func runTest() async {
        guard let url = URL(string: "http://127.0.0.1:8787/llm/chat") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.addValue(Keychain.get("FTGControlToken") ?? UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token", forHTTPHeaderField: "X-FTG-Token")
        req.addValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = ["prompt": prompt]
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            output = String(data: data, encoding: .utf8) ?? ""
        } catch {
            output = "Error: \(error.localizedDescription)"
        }
    }

    private func loadProviders() async {
        guard let url = URL(string: "http://127.0.0.1:8787/llm/providers") else { return }
        var req = URLRequest(url: url)
        req.addValue(UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token", forHTTPHeaderField: "X-FTG-Token")
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            if let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                providers = (obj["providers"] as? [[String: Any]]) ?? []
                if let first = providers.first, let url = first["base_url"] as? String { selectedBaseURL = url }
            }
        } catch {}
    }

    private func applyConfig() async {
        guard let url = URL(string: "http://127.0.0.1:8787/llm/config") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.addValue(UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token", forHTTPHeaderField: "X-FTG-Token")
        req.addValue("application/json", forHTTPHeaderField: "Content-Type")
        var payload: [String: Any] = [
            "base_url": selectedBaseURL,
            "model": model,
            "request_timeout_seconds": Int(timeout) ?? 60
        ]
        if !apiKey.isEmpty { payload["api_key"] = apiKey }
        req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        do { _ = try await URLSession.shared.data(for: req) } catch {}
    }
}

import WebKit

struct WebPanelContainer: View {
    let appLang: String
    @State private var urlText: String = UserDefaults.standard.string(forKey: "WebPanelURL") ?? "http://127.0.0.1:8787/ui"
    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                TextField(appLang == "ru" ? "URL Веб-панели" : "Web URL", text: $urlText)
                Button(appLang == "ru" ? "Открыть" : "Open") {
                    UserDefaults.standard.set(urlText, forKey: "WebPanelURL")
                }
            }
            Divider()
            WebPanelView(urlString: urlText)
        }.padding()
    }
}

struct WebPanelView: NSViewRepresentable {
    var urlString: String
    func makeNSView(context: Context) -> WKWebView {
        let v = WKWebView()
        if let url = URL(string: urlString) { v.load(URLRequest(url: url)) }
        return v
    }
    func updateNSView(_ nsView: WKWebView, context: Context) {
        if let url = URL(string: urlString) {
            nsView.load(URLRequest(url: url))
        }
    }
}

struct LogsView: View {
    let appLang: String
    @State private var lines: [String] = []
    @State private var autoRefresh = true
    var body: some View {
        VStack(alignment: .leading) {
            HStack {
                Button(appLang == "ru" ? "Обновить" : "Refresh") { Task { await refresh() } }
                Toggle(appLang == "ru" ? "Автоматическая обновление" : "Auto refresh", isOn: $autoRefresh).toggleStyle(.switch)
                Button(appLang == "ru" ? "Копировать" : "Copy") { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(lines.joined(separator: "\n"), forType: .string) }
                Spacer()
            }
            Divider()
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 2) {
                    ForEach(lines.indices, id: \.self) { i in
                        Text(lines[i]).font(.system(size: 12, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
        }.padding().task { await loop() }
    }
    private func loop() async {
        while true {
            if autoRefresh { await refresh() }
            try? await Task.sleep(nanoseconds: 1_000_000_000)
        }
    }
    private func refresh() async {
        guard let url = URL(string: "http://127.0.0.1:8787/logs/tail?lines=200") else { return }
        var req = URLRequest(url: url)
        req.addValue(Keychain.get("FTGControlToken") ?? UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token", forHTTPHeaderField: "X-FTG-Token")
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            if let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                self.lines = (obj["lines"] as? [String]) ?? []
            }
        } catch {
            self.lines = ["Error: \(error.localizedDescription)"]
        }
    }
}

struct ShortcutsView: View {
    let appLang: String
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(appLang == "ru" ? "Быстрые действия через /exec появятся здесь." : "Quick actions via /exec will appear here.")
            Spacer()
        }.padding()
    }
}

struct MessagesView: View {
    let appLang: String
    @State private var chat: String = "me"
    @State private var text: String = "Hello from FTG"
    @State private var result: String = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            TextField(appLang == "ru" ? "Чат (имя пользователя или ID)" : "Chat (username or ID)", text: $chat)
            TextField(appLang == "ru" ? "Текст" : "Text", text: $text)
            HStack {
                Button(appLang == "ru" ? "Отправить" : "Send") { Task { await send() } }
            }
            ScrollView { Text(result).frame(maxWidth: .infinity, alignment: .leading) }
            Spacer()
        }.padding()
    }
    private func send() async {
        guard let url = URL(string: "http://127.0.0.1:8787/send_message") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.addValue(UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token", forHTTPHeaderField: "X-FTG-Token")
        req.addValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["chat": chat, "text": text])
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            result = String(data: data, encoding: .utf8) ?? ""
        } catch {
            result = "Error: \(error.localizedDescription)"
        }
    }
}

struct ServerSettingsView: View {
    let appLang: String
    @State private var token: String = Keychain.get("FTGControlToken") ?? UserDefaults.standard.string(forKey: "FTGControlToken") ?? ""
    @State private var pingResult: String = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(appLang == "ru" ? "Токен сервера FTG Control" : "FTG Control Server Token").font(.headline)
            SecureField(appLang == "ru" ? "Введите токен сервера FTG Control" : "Enter FTG control token", text: $token)
                .textFieldStyle(.roundedBorder)
            HStack(spacing: 12) {
                Button(appLang == "ru" ? "Сохранить токен" : "Save Token") {
                    _ = Keychain.set(token, for: "FTGControlToken")
                    UserDefaults.standard.set(token, forKey: "FTGControlToken")
                }
                Button(appLang == "ru" ? "Пинг /health" : "Ping /health") { Task { await ping() } }
            }
            if !pingResult.isEmpty { Text(pingResult).font(.caption).foregroundStyle(.secondary) }
            Spacer()
        }.padding()
    }
    private func ping() async {
        do {
            let res = try await ControlClient.shared.getHealth()
            pingResult = "Health: \(res.status), FTG: \(res.ftg)"
        } catch {
            pingResult = "Ping failed: \(error.localizedDescription)"
        }
    }
}

struct BotSettingsView: View {
    let appLang: String
    @State private var autoReplyEnabled: Bool = false
    @State private var autoReplyMode: String = "off"
    @State private var allowlist: String = ""
    @State private var blocklist: String = ""
    @State private var silentReading: Bool = true
    @State private var minReplyInterval: String = "5"
    @State private var replyPrompt: String = ""
    @State private var status: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                Button(appLang == "ru" ? "Загрузить" : "Load") { Task { await load() } }
                Button(appLang == "ru" ? "Сохранить" : "Save") { Task { await save() } }
                if !status.isEmpty { Text(status).font(.caption).foregroundStyle(.secondary) }
            }
            Toggle(appLang == "ru" ? "Автоматическое ответление" : "Auto reply enabled", isOn: $autoReplyEnabled)
            Picker(appLang == "ru" ? "Режим автоматического ответа" : "Auto reply mode", selection: $autoReplyMode) {
                Text("Off").tag("off")
                Text("Mentions only").tag("mentions_only")
                Text("All").tag("all")
            }
            TextField(appLang == "ru" ? "Разрешенные чаты (через запятую)" : "Allowed chats (comma-separated)", text: $allowlist)
            TextField(appLang == "ru" ? "Заблокированные чаты (через запятую)" : "Blocked chats (comma-separated)", text: $blocklist)
            Toggle(appLang == "ru" ? "Беззвучное чтение (не отмечать прочитанным)" : "Silent reading (do not mark read)", isOn: $silentReading)
            TextField(appLang == "ru" ? "Минимальный интервал ответа (сек)" : "Min reply interval (sec)", text: $minReplyInterval)
                .textFieldStyle(.roundedBorder)
            TextField(appLang == "ru" ? "Системный запрос (prompt)" : "Reply prompt (system)", text: $replyPrompt)
            Spacer()
        }.padding()
    }

    private func load() async {
        guard let url = URL(string: "http://127.0.0.1:8787/bot/config") else { return }
        var req = URLRequest(url: url)
        req.addValue(Keychain.get("FTGControlToken") ?? UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token", forHTTPHeaderField: "X-FTG-Token")
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            if let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let cfg = obj["config"] as? [String: Any] {
                autoReplyEnabled = (cfg["auto_reply_enabled"] as? Bool) ?? false
                autoReplyMode = (cfg["auto_reply_mode"] as? String) ?? "off"
                let allow = (cfg["allowlist_chats"] as? [Any])?.compactMap { String(describing: $0) } ?? []
                allowlist = allow.joined(separator: ",")
                let block = (cfg["blocklist_chats"] as? [Any])?.compactMap { String(describing: $0) } ?? []
                blocklist = block.joined(separator: ",")
                silentReading = (cfg["silent_reading"] as? Bool) ?? true
                if let v = cfg["min_reply_interval_seconds"] as? Int { minReplyInterval = String(v) }
                replyPrompt = (cfg["reply_prompt"] as? String) ?? ""
                status = "Loaded"
            }
        } catch { status = "Load failed: \(error.localizedDescription)" }
    }

    private func save() async {
        guard let url = URL(string: "http://127.0.0.1:8787/bot/config") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.addValue(Keychain.get("FTGControlToken") ?? UserDefaults.standard.string(forKey: "FTGControlToken") ?? "changeme_local_token", forHTTPHeaderField: "X-FTG-Token")
        req.addValue("application/json", forHTTPHeaderField: "Content-Type")
        var payload: [String: Any] = [
            "auto_reply_enabled": autoReplyEnabled,
            "auto_reply_mode": autoReplyMode,
            "silent_reading": silentReading,
            "reply_prompt": replyPrompt
        ]
        if let n = Int(minReplyInterval) { payload["min_reply_interval_seconds"] = n }
        if !allowlist.trimmingCharacters(in: .whitespaces).isEmpty {
            payload["allowlist_chats"] = allowlist.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }
        }
        if !blocklist.trimmingCharacters(in: .whitespaces).isEmpty {
            payload["blocklist_chats"] = blocklist.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }
        }
        req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            if let _ = try JSONSerialization.jsonObject(with: data) as? [String: Any] { status = "Saved" }
        } catch { status = "Save failed: \(error.localizedDescription)" }
    }
}