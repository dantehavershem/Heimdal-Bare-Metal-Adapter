/*
 * Bare-Metal Adapter - WinPE bridge
 * Minimal native x64 Windows executable, no CRT dependency.
 * Its only job is to execute STAGE.CMD from the same directory
 * and return its exit code to the caller.
 */

typedef unsigned long DWORD;
typedef int BOOL;
typedef unsigned short WCHAR;
typedef void *HANDLE;
typedef void *LPVOID;
typedef const WCHAR *LPCWSTR;
typedef WCHAR *LPWSTR;
typedef unsigned long long ULONG_PTR;

#define TRUE 1
#define FALSE 0
#define INFINITE 0xFFFFFFFFUL
#define CREATE_NO_WINDOW 0x08000000UL

#define WINAPI __attribute__((ms_abi))
#define DLLIMPORT __declspec(dllimport)

typedef struct _STARTUPINFOW {
    DWORD cb;
    LPWSTR lpReserved;
    LPWSTR lpDesktop;
    LPWSTR lpTitle;
    DWORD dwX;
    DWORD dwY;
    DWORD dwXSize;
    DWORD dwYSize;
    DWORD dwXCountChars;
    DWORD dwYCountChars;
    DWORD dwFillAttribute;
    DWORD dwFlags;
    unsigned short wShowWindow;
    unsigned short cbReserved2;
    unsigned char *lpReserved2;
    HANDLE hStdInput;
    HANDLE hStdOutput;
    HANDLE hStdError;
} STARTUPINFOW;

typedef struct _PROCESS_INFORMATION {
    HANDLE hProcess;
    HANDLE hThread;
    DWORD dwProcessId;
    DWORD dwThreadId;
} PROCESS_INFORMATION;

DLLIMPORT DWORD WINAPI GetModuleFileNameW(HANDLE hModule, LPWSTR lpFilename, DWORD nSize);
DLLIMPORT BOOL WINAPI CreateProcessW(LPCWSTR lpApplicationName, LPWSTR lpCommandLine,
    LPVOID lpProcessAttributes, LPVOID lpThreadAttributes, BOOL bInheritHandles,
    DWORD dwCreationFlags, LPVOID lpEnvironment, LPCWSTR lpCurrentDirectory,
    STARTUPINFOW *lpStartupInfo, PROCESS_INFORMATION *lpProcessInformation);
DLLIMPORT DWORD WINAPI WaitForSingleObject(HANDLE hHandle, DWORD dwMilliseconds);
DLLIMPORT BOOL WINAPI GetExitCodeProcess(HANDLE hProcess, DWORD *lpExitCode);
DLLIMPORT BOOL WINAPI CloseHandle(HANDLE hObject);
DLLIMPORT void WINAPI ExitProcess(DWORD uExitCode);

static WCHAR g_module[1024];
static WCHAR g_script[1200];
static WCHAR g_cmdline[1600];

static unsigned long wlen(const WCHAR *s) {
    unsigned long n = 0;
    while (s[n]) n++;
    return n;
}

static void wcopy(WCHAR *dst, const WCHAR *src) {
    while ((*dst++ = *src++)) { }
}

static void append(WCHAR *dst, const WCHAR *src) {
    unsigned long n = wlen(dst);
    wcopy(dst + n, src);
}

static void dirname_inplace(WCHAR *path) {
    unsigned long n = wlen(path);
    while (n > 0) {
        WCHAR c = path[n - 1];
        if (c == '\\' || c == '/') {
            path[n] = 0;
            return;
        }
        n--;
    }
    path[0] = 0;
}

void mainCRTStartup(void) {
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD exitCode = 90;
    unsigned long i;

    for (i = 0; i < sizeof(si); i++) ((unsigned char*)&si)[i] = 0;
    for (i = 0; i < sizeof(pi); i++) ((unsigned char*)&pi)[i] = 0;
    si.cb = sizeof(si);

    if (!GetModuleFileNameW((HANDLE)0, g_module, 1024)) ExitProcess(91);
    dirname_inplace(g_module);

    wcopy(g_script, g_module);
    append(g_script, (const WCHAR*)L"STAGE.CMD");

    wcopy(g_cmdline, (const WCHAR*)L"cmd.exe /d /c \"\"");
    append(g_cmdline, g_script);
    append(g_cmdline, (const WCHAR*)L"\"\"");

    if (!CreateProcessW((LPCWSTR)0, g_cmdline, (LPVOID)0, (LPVOID)0, FALSE,
                        0, (LPVOID)0, g_module, &si, &pi)) {
        ExitProcess(92);
    }

    WaitForSingleObject(pi.hProcess, INFINITE);
    if (!GetExitCodeProcess(pi.hProcess, &exitCode)) exitCode = 93;
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    ExitProcess(exitCode);
}
