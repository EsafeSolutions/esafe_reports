package lk.esafe.blabs;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/** Native Android launcher for the same-origin, authenticated ESAFE reporting app. */
public final class MainActivity extends Activity {
    private static final String HOST = "osaka.cloud.esafe.lk";
    private static final String HOME = "https://" + HOST + "/esafe-report/mobile?tab=products";
    private WebView web;
    private ProgressBar progress;
    private TextView error;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.WHITE);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets.consumeSystemWindowInsets();
        });
        LinearLayout toolbar = new LinearLayout(this);
        Button home = new Button(this); home.setText("Home"); home.setContentDescription("Open products");
        home.setOnClickListener(v -> web.loadUrl(HOME)); toolbar.addView(home);
        TextView site = new TextView(this); site.setText("ESAFE · Osaka"); site.setTextColor(Color.rgb(17, 38, 74)); site.setTextSize(14);
        site.setGravity(android.view.Gravity.CENTER); toolbar.addView(site, new LinearLayout.LayoutParams(0, -1, 1));
        Button retry = new Button(this); retry.setText("Refresh"); retry.setOnClickListener(v -> { error.setVisibility(android.view.View.GONE); if (trusted(web.getUrl())) web.reload(); else web.loadUrl(HOME); });
        toolbar.addView(retry); root.addView(toolbar, new LinearLayout.LayoutParams(-1, dp(44)));
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        root.addView(progress, new LinearLayout.LayoutParams(-1, dp(3)));
        error = new TextView(this); error.setText("Unable to connect. Check your internet connection, then tap Refresh.");
        error.setTextSize(15); error.setTextColor(Color.rgb(160, 35, 48)); error.setPadding(dp(20), dp(14), dp(20), dp(14));
        error.setVisibility(android.view.View.GONE); error.setAccessibilityLiveRegion(android.view.View.ACCESSIBILITY_LIVE_REGION_POLITE); root.addView(error);
        web = new WebView(this);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true); settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false); settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setUserAgentString(settings.getUserAgentString() + " EsafeNative/1.0 Android");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
        web.addJavascriptInterface(new ShareBridge(), "EsafeNative");
        web.setWebChromeClient(new android.webkit.WebChromeClient() {
            @Override public void onProgressChanged(WebView view, int value) {
                progress.setProgress(value); progress.setVisibility(value == 100 ? android.view.View.GONE : android.view.View.VISIBLE);
            }
        });
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (trusted(uri.toString())) return false;
                if (request.isForMainFrame() && ("https".equals(uri.getScheme()) || "mailto".equals(uri.getScheme()) || "tel".equals(uri.getScheme()))) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) { }
                }
                return true;
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap icon) { error.setVisibility(android.view.View.GONE); }
            @Override public void onPageFinished(WebView view, String url) { CookieManager.getInstance().flush(); }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError failure) {
                if (request.isForMainFrame()) error.setVisibility(android.view.View.VISIBLE);
            }
        });
        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1)); setContentView(root);
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, () -> navigateBack());
        }
        if (state == null || web.restoreState(state) == null) web.loadUrl(HOME);
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private boolean trusted(String value) {
        if (value == null) return false;
        Uri uri = Uri.parse(value);
        return "https".equals(uri.getScheme()) && HOST.equalsIgnoreCase(uri.getHost()) && (uri.getPort() == -1 || uri.getPort() == 443) && uri.getUserInfo() == null;
    }
    @Override protected void onSaveInstanceState(Bundle state) { super.onSaveInstanceState(state); web.saveState(state); }
    private void navigateBack() { if (web.canGoBack()) web.goBack(); else finish(); }
    @Override public void onBackPressed() { navigateBack(); }
    @Override protected void onPause() { CookieManager.getInstance().flush(); web.onPause(); super.onPause(); }
    @Override protected void onResume() { super.onResume(); if (web != null) web.onResume(); }
    @Override protected void onDestroy() { web.removeJavascriptInterface("EsafeNative"); web.destroy(); super.onDestroy(); }

    public final class ShareBridge {
        @JavascriptInterface public void shareCsv(String filename, String content) {
            if (filename == null || !filename.matches("[A-Za-z0-9._-]+\\.csv") || content == null || content.length() > 2_000_000) return;
            runOnUiThread(() -> {
                if (!trusted(web.getUrl())) return;
                try {
                    File folder = new File(getCacheDir(), "exports"); folder.mkdirs();
                    File file = new File(folder, filename);
                    try (FileOutputStream stream = new FileOutputStream(file)) { stream.write(content.getBytes(StandardCharsets.UTF_8)); }
                    Uri uri = Uri.parse("content://lk.esafe.blabs.exports/" + filename);
                    Intent share = new Intent(Intent.ACTION_SEND); share.setType("text/csv");
                    share.putExtra(Intent.EXTRA_STREAM, uri); share.setClipData(ClipData.newRawUri(filename, uri));
                    share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    startActivity(Intent.createChooser(share, "Export ESAFE report"));
                } catch (Exception failure) { new AlertDialog.Builder(MainActivity.this).setMessage("Unable to export this report. Please try again.").setPositiveButton("OK", null).show(); }
            });
        }
    }
}
