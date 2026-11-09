// Linux integration test of the loaded plugin's native approval dialog.
// Defer renderer startup while exercising the actual OBS source and Qt callbacks.
#include <obs.h>
#include <obs-nix-platform.h>
#include <QApplication>
#include <QDialog>
#include <QDialogButtonBox>
#include <QKeyEvent>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QTemporaryDir>
#include <QTimer>
#include <cstdio>
#include <cstdlib>

extern "C" __attribute__((visibility("default"))) void obs_browser_initialize() {}

static void require(bool ok, const char *message)
{
	if (!ok) {
		std::fprintf(stderr, "FAIL %s\n", message);
		std::exit(1);
	}
}

int main(int argc, char **argv)
{
	QApplication app(argc, argv);
	require(argc == 3, "expected the plugin .so path and locale data directory");
	QTemporaryDir config;
	require(config.isValid(), "could not create temporary config");
	obs_set_nix_platform(OBS_NIX_PLATFORM_X11_EGL);
	require(obs_startup("en-US", config.path().toUtf8().constData(), nullptr), "OBS startup requires an X display");
	obs_module_t *module = nullptr;
	require(obs_open_module(&module, argv[1], argv[2]) == MODULE_SUCCESS && obs_init_module(module), "module load");

	const char *script = "document.title = 'reviewed'";
	obs_data_t *draft = obs_data_create();
	obs_data_set_string(draft, "url", "https://example.invalid/overlay");
	obs_data_set_string(draft, "javascript", script);
	obs_source_t *source = obs_source_create("browser_source", "review-test", draft, nullptr);
	require(source != nullptr, "source creation");
	obs_properties_t *props = obs_source_properties(source);
	obs_property_t *button = obs_properties_get(props, "approve_javascript");
	obs_data_t *settings = obs_source_get_settings(source);
	require(button != nullptr, "missing approval button");
	constexpr char request[] = "_javascript_approval_request";

	for (bool accept : {false, true}) {
		bool shown = false;
		QTimer::singleShot(0, [&]() {
			auto *dialog = qobject_cast<QDialog *>(QApplication::activeModalWidget());
			require(dialog != nullptr, "missing local review dialog");
			auto *code = dialog->findChild<QPlainTextEdit *>();
			auto *buttons = dialog->findChild<QDialogButtonBox *>();
			require(code && code->isReadOnly() && code->toPlainText() == script,
				"unexpected script in review");
			require(buttons != nullptr, "missing dialog buttons");
			auto *cancel = buttons->button(QDialogButtonBox::Cancel);
			auto *yes = buttons->button(QDialogButtonBox::Yes);
			require(cancel && yes && cancel->isDefault() && !yes->isDefault() &&
					dialog->focusWidget() == cancel,
				"Cancel must be the focused default");
			shown = true;
			if (accept) {
				yes->click();
			} else {
				QKeyEvent enter(QEvent::KeyPress, Qt::Key_Return, Qt::NoModifier);
				QApplication::sendEvent(cancel, &enter);
				require(!dialog->isVisible(), "Enter did not dismiss the review");
			}
		});
		obs_property_button_clicked(button, source);
		require(shown, "property button failed to open the dialog");
		require(bool(*obs_data_get_string(settings, request)) == accept,
			"unexpected approval request after review");
	}

	std::puts("PASS Enter cancels review and explicit consent creates a one-time request");
	obs_data_release(settings);
	obs_properties_destroy(props);
	obs_data_release(draft);
	config.remove();
	// Source teardown posts a CEF task. This process deliberately never starts CEF.
	std::fflush(stdout);
	std::_Exit(EXIT_SUCCESS);
}
