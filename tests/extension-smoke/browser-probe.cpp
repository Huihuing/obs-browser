// Exercise the fork's BrowserApp with the same windowless, global-context browser used by Browser Source.
#include "browser-app.hpp"
#include "include/base/cef_callback.h"
#include "include/wrapper/cef_closure_task.h"
#include <nlohmann/json.hpp>
#include <cstdlib>
#include <iostream>
#include <string_view>

class ProbeClient : public CefClient, public CefRenderHandler, public CefDisplayHandler, public CefLifeSpanHandler {
public:
	CefRefPtr<CefRenderHandler> GetRenderHandler() override { return this; }
	CefRefPtr<CefDisplayHandler> GetDisplayHandler() override { return this; }
	CefRefPtr<CefLifeSpanHandler> GetLifeSpanHandler() override { return this; }
	void GetViewRect(CefRefPtr<CefBrowser>, CefRect &rect) override { rect = CefRect(0, 0, 640, 480); }
	void OnPaint(CefRefPtr<CefBrowser>, PaintElementType, const RectList &, const void *, int, int) override {}
	void OnTitleChange(CefRefPtr<CefBrowser> browser, const CefString &title) override
	{
		if (title.ToString().starts_with("Content script:")) {
			std::cout << title.ToString() << std::endl;
			// Chromium is notifying WebContents observers in this callback.
			CefPostTask(TID_UI, base::BindOnce(
						    [](CefRefPtr<CefBrowser> finished) {
							    finished->GetHost()->WasHidden(true);
							    finished->GetHost()->CloseBrowser(true);
						    },
						    browser));
		}
	}
	void OnBeforeClose(CefRefPtr<CefBrowser>) override
	{
		std::cerr << "Probe browser closed" << std::endl;
		CefQuitMessageLoop();
	}

	IMPLEMENT_REFCOUNTING(ProbeClient);
};

class ProbeApp : public BrowserApp {
public:
	void OnContextInitialized() override
	{
		BrowserApp::OnContextInitialized();
		CefWindowInfo window;
		window.bounds.width = 640;
		window.bounds.height = 480;
		window.windowless_rendering_enabled = true;
		auto browser = CefBrowserHost::CreateBrowserSync(window, new ProbeClient, std::getenv("OBS_PROBE_URL"),
								 CefBrowserSettings{}, nullptr, nullptr);
		if (!browser) {
			CefQuitMessageLoop();
		}
	}
};

int main(int argc, char **argv)
{
	CefRefPtr<ProbeApp> app = new ProbeApp;
	if (const char *saved = std::getenv("OBS_PROBE_SAVED_EXTENSIONS")) {
		app->SetStartupExtensions(nlohmann::json::parse(saved).get<std::vector<std::string>>());
	}
	if (argc > 1 && std::string_view(argv[1]) == "--check-policy") {
		auto line = CefCommandLine::CreateCommandLine();
		line->InitFromArgv(argc, argv);
		app->OnBeforeCommandLineProcessing({}, line);
		std::cout << "disabled=" << line->HasSwitch("disable-extensions")
			  << " allow=" << line->GetSwitchValue("disable-extensions-except").ToString()
			  << " load=" << line->GetSwitchValue("load-extension").ToString() << std::endl;
		return 0;
	}

	CefMainArgs args(argc, argv);
	int child = CefExecuteProcess(args, app, nullptr);
	if (child >= 0) {
		return child;
	}
	CefSettings settings;
	settings.no_sandbox = true;
	settings.windowless_rendering_enabled = true;
	CefString(&settings.cache_path) = std::getenv("OBS_PROBE_PROFILE");
	CefString(&settings.root_cache_path) = std::getenv("OBS_PROBE_PROFILE");
	if (!CefInitialize(args, settings, app, nullptr)) {
		return 1;
	}
	CefRunMessageLoop();
	std::cerr << "Probe shutting down CEF" << std::endl;
	CefShutdown();
	app = nullptr;
	return 0;
}
