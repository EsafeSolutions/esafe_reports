import SwiftUI
import WebKit
import UIKit

private let appHost = "osaka.cloud.esafe.lk"
private let appHome = URL(string: "https://osaka.cloud.esafe.lk/esafe-report/mobile?tab=products")!

struct ContentView: View {
    @State private var loading = true
    @State private var failed = false
    @State private var action = UUID()
    @State private var goHome = false

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button("Home") { goHome = true; action = UUID() }
                Spacer()
                Text("ESAFE · Osaka").font(.subheadline).foregroundStyle(Color(red: 17/255, green: 38/255, blue: 74/255))
                Spacer()
                Button("Refresh") { goHome = false; action = UUID() }
            }.padding(.horizontal, 16).frame(height: 44)
            if loading { ProgressView().progressViewStyle(.linear).tint(.teal) }
            if failed {
                Text("Unable to connect. Check your internet connection, then tap Refresh.")
                    .font(.subheadline).foregroundStyle(.red).padding()
                    .accessibilityAddTraits(.updatesFrequently)
            }
            ReportWebView(loading: $loading, failed: $failed, action: action, goHome: goHome)
        }.background(.white).tint(Color(red: 0, green: 143/255, blue: 131/255))
    }
}

private func trusted(_ url: URL) -> Bool {
    url.scheme == "https" && url.host?.lowercased() == appHost && (url.port == nil || url.port == 443) && url.user == nil && url.password == nil
}

struct ReportWebView: UIViewRepresentable {
    @Binding var loading: Bool
    @Binding var failed: Bool
    let action: UUID
    let goHome: Bool

    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.applicationNameForUserAgent = "EsafeNative/1.0 iOS"
        config.userContentController.add(context.coordinator, name: "esafeShare")
        let web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = context.coordinator
        web.allowsBackForwardNavigationGestures = true
        web.scrollView.contentInsetAdjustmentBehavior = .never
        web.isOpaque = false
        web.backgroundColor = .white
        context.coordinator.lastAction = action
        web.load(URLRequest(url: appHome))
        return web
    }
    func updateUIView(_ web: WKWebView, context: Context) {
        context.coordinator.parent = self
        guard context.coordinator.lastAction != action else { return }
        context.coordinator.lastAction = action
        if goHome || (web.url.map({ !trusted($0) }) ?? true) { web.load(URLRequest(url: appHome)) }
        else { web.reload() }
    }
    static func dismantleUIView(_ web: WKWebView, coordinator: Coordinator) {
        web.configuration.userContentController.removeScriptMessageHandler(forName: "esafeShare")
        web.stopLoading()
        web.navigationDelegate = nil
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        var parent: ReportWebView
        var lastAction: UUID?
        init(_ parent: ReportWebView) { self.parent = parent }
        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            parent.loading = true; parent.failed = false
        }
        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { parent.loading = false }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            if (error as NSError).code != NSURLErrorCancelled { parent.loading = false; parent.failed = true }
        }
        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            parent.loading = false; parent.failed = true
        }
        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
            if trusted(url) {
                if navigationAction.targetFrame == nil { webView.load(navigationAction.request); decisionHandler(.cancel) }
                else { decisionHandler(.allow) }
                return
            }
            if navigationAction.targetFrame?.isMainFrame != false && ["https", "mailto", "tel"].contains(url.scheme ?? "") {
                UIApplication.shared.open(url)
            }
            decisionHandler(.cancel)
        }
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.frameInfo.isMainFrame, let source = message.frameInfo.request.url, trusted(source),
                  let body = message.body as? [String: String], let filename = body["filename"], let content = body["content"],
                  filename.range(of: "^[A-Za-z0-9._-]+\\.csv$", options: .regularExpression) != nil,
                  content.utf8.count <= 2_000_000 else { return }
            do {
                let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ESAFE-exports", isDirectory: true)
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                let file = directory.appendingPathComponent(filename)
                try content.write(to: file, atomically: true, encoding: .utf8)
                let share = UIActivityViewController(activityItems: [file], applicationActivities: nil)
                guard let scene = UIApplication.shared.connectedScenes.first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene,
                      var controller = scene.windows.first(where: { $0.isKeyWindow })?.rootViewController else { return }
                while let presented = controller.presentedViewController { controller = presented }
                share.popoverPresentationController?.sourceView = controller.view
                share.popoverPresentationController?.sourceRect = CGRect(x: controller.view.bounds.midX, y: controller.view.bounds.midY, width: 1, height: 1)
                controller.present(share, animated: true)
            } catch { parent.failed = true }
        }
    }
}
