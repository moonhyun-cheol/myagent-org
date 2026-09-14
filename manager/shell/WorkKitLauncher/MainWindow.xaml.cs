using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using CqrPa.Shell;
using Microsoft.Web.WebView2.Core;
using Application = System.Windows.Application;
using MessageBox = System.Windows.MessageBox;

namespace CqrPa.WorkKitLauncher;

public partial class MainWindow : Window
{
    private readonly string _cqrRoot;
    private readonly int _port;
    private readonly ApiProcessHost _api;
    private bool _loading;
    private bool _webViewHooked;

    internal LauncherUpdatePollingService? UpdatePolling { get; set; }

    public MainWindow(string cqrRoot, int port, ApiProcessHost api)
    {
        _cqrRoot = cqrRoot;
        _port = port;
        _api = api;
        InitializeComponent();
        Loaded += async (_, _) => await LoadUiAsync();
    }

    internal void BringToFront()
    {
        Show();
        Activate();
        WindowState = WindowState.Normal;
    }

    internal void PrepareForUpdateExit()
    {
        if (Application.Current is App app) app.PrepareForLauncherUpdateExit();
    }

    private async Task LoadUiAsync()
    {
        if (_loading) return;
        _loading = true;
        LoadingOverlay.Visibility = Visibility.Visible;
        RetryButton.Visibility = Visibility.Collapsed;
        StatusText.Text = "로컬 서비스를 준비하는 중…";

        try
        {
            if (!await _api.WaitForHealthAsync(_api.RecommendedHealthTimeout))
                throw new InvalidOperationException("Core API가 준비되지 않았습니다.");

            StatusText.Text = "화면을 불러오는 중…";
            var launcherUrl = $"http://127.0.0.1:{_port}/launcher/";
            var webDir = ResolveLauncherWebDir(_cqrRoot)
                ?? throw new InvalidOperationException("관리자 화면 파일(web/index.html)을 찾지 못했습니다.");

            var userData = Path.Combine(_cqrRoot, "data", "work-kit-launcher-webview");
            Directory.CreateDirectory(userData);
            var env = await CoreWebView2Environment.CreateAsync(
                browserExecutableFolder: null,
                userDataFolder: userData,
                options: new CoreWebView2EnvironmentOptions());

            await WebView.EnsureCoreWebView2Async(env);
            var core = WebView.CoreWebView2
                ?? throw new InvalidOperationException("WebView2를 초기화하지 못했습니다.");

            core.Settings.AreDevToolsEnabled = false;
            core.Settings.AreBrowserAcceleratorKeysEnabled = false;
            if (!_webViewHooked)
            {
                core.AddWebResourceRequestedFilter(
                    $"http://127.0.0.1:{_port}/launcher*",
                    CoreWebView2WebResourceContext.All);
                core.WebResourceRequested += (_, args) => ServeLauncherWebResource(args, core, webDir);
                core.WebMessageReceived += OnWebMessageReceived;
                core.NavigationCompleted += OnNavigationCompleted;
                var script = JsonSerializer.Serialize(new
                {
                    baseUrl = $"http://127.0.0.1:{_port}",
                    port = _port,
                    cqrRoot = _cqrRoot,
                });
                await core.AddScriptToExecuteOnDocumentCreatedAsync(
                    $"window.__MY_AGENT_API__ = {script};");
                _webViewHooked = true;
            }

            WebView.Source = new Uri(launcherUrl);
        }
        catch (Exception ex)
        {
            StatusText.Text = ex.Message;
            RetryButton.Visibility = Visibility.Visible;
        }
        finally
        {
            _loading = false;
        }
    }

    private static string? ResolveLauncherWebDir(string cqrRoot)
    {
        var candidates = new[]
        {
            Path.Combine(AppContext.BaseDirectory, "web"),
            Path.Combine(cqrRoot, "bin", "work-kit-launcher", "web"),
            Path.Combine(cqrRoot, "ui", "work-kit-launcher", "dist"),
        };
        return candidates.FirstOrDefault(dir => File.Exists(Path.Combine(dir, "index.html")));
    }

    private static void ServeLauncherWebResource(
        CoreWebView2WebResourceRequestedEventArgs args,
        CoreWebView2 core,
        string webDir)
    {
        if (!Uri.TryCreate(args.Request.Uri, UriKind.Absolute, out var uri)) return;
        if (!uri.AbsolutePath.StartsWith("/launcher", StringComparison.OrdinalIgnoreCase)) return;

        var relative = uri.AbsolutePath.Equals("/launcher", StringComparison.OrdinalIgnoreCase)
            || uri.AbsolutePath.Equals("/launcher/", StringComparison.OrdinalIgnoreCase)
            ? "index.html"
            : Uri.UnescapeDataString(uri.AbsolutePath["/launcher/".Length..]).Replace('/', Path.DirectorySeparatorChar);
        if (string.IsNullOrWhiteSpace(relative) || relative.EndsWith(Path.DirectorySeparatorChar))
            relative = Path.Combine(relative, "index.html");

        var webRoot = Path.GetFullPath(webDir);
        var webPrefix = webRoot.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
            + Path.DirectorySeparatorChar;
        var full = Path.GetFullPath(Path.Combine(webRoot, relative));
        if (!full.StartsWith(webPrefix, StringComparison.OrdinalIgnoreCase) || !File.Exists(full))
        {
            args.Response = core.Environment.CreateWebResourceResponse(
                new MemoryStream(Array.Empty<byte>()), 404, "Not Found", "Content-Type: text/plain; charset=utf-8");
            return;
        }

        args.Response = core.Environment.CreateWebResourceResponse(
            File.OpenRead(full),
            200,
            "OK",
            $"Content-Type: {MimeTypeFor(full)}\r\nCache-Control: no-cache");
    }

    private static string MimeTypeFor(string path) => Path.GetExtension(path).ToLowerInvariant() switch
    {
        ".html" => "text/html; charset=utf-8",
        ".js" => "text/javascript; charset=utf-8",
        ".css" => "text/css; charset=utf-8",
        ".json" => "application/json; charset=utf-8",
        ".svg" => "image/svg+xml",
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".ico" => "image/x-icon",
        ".woff" => "font/woff",
        ".woff2" => "font/woff2",
        ".map" => "application/json",
        _ => "application/octet-stream",
    };

    private void OnNavigationCompleted(object? sender, CoreWebView2NavigationCompletedEventArgs e)
    {
        if (!e.IsSuccess)
        {
            StatusText.Text = "화면을 불러오지 못했습니다.";
            RetryButton.Visibility = Visibility.Visible;
            return;
        }

        LoadingOverlay.Visibility = Visibility.Collapsed;
    }

    private void OnWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        try
        {
            using var doc = JsonDocument.Parse(e.WebMessageAsJson);
            var type = doc.RootElement.TryGetProperty("type", out var t) ? t.GetString() : null;
            if (type == "launcher.launchMyAgent")
                LaunchMyAgent();
        }
        catch
        {
            /* ignore malformed messages */
        }
    }

    private void LaunchMyAgent()
    {
        var candidates = new[]
        {
            Path.Combine(_cqrRoot, "bin", "my-agent", "MYAgent.exe"),
            Path.Combine(_cqrRoot, "MYAgent.exe"),
        };
        var exe = candidates.FirstOrDefault(File.Exists);
        if (exe is null)
        {
            MessageBox.Show(
                "MYAgent.exe를 찾지 못했습니다. MY Agent를 먼저 설치하세요.",
                "MY Agent 관리자",
                MessageBoxButton.OK,
                MessageBoxImage.Warning);
            return;
        }

        var psi = new ProcessStartInfo
        {
            FileName = exe,
            WorkingDirectory = Path.GetDirectoryName(exe) ?? _cqrRoot,
            UseShellExecute = false,
        };
        psi.Environment["MY_AGENT_ROOT"] = _cqrRoot;
        psi.Environment["CQR_API_PORT"] = _port.ToString();
        Process.Start(psi);
    }

    private async void OnRetryClick(object sender, RoutedEventArgs e)
    {
        await LoadUiAsync();
    }
}
