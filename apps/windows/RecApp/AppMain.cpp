#ifdef _WIN32
#include <windows.h>
#else
int main() { return 0; }
#endif

// The packaged WinUI 3 entry point is intentionally kept as the only process
// entry. Capture/local custody are constructed by the app shell, never by the
// WebView document lifecycle.
#ifdef _WIN32
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) { return 0; }
#endif
