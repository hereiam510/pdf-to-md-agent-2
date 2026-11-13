// Acceptance-only reader. No ExifTool configuration, source map, or write API.
#include <string>
#include <iostream>
#include <windows.h>
#define TXMP_STRING_TYPE std::string
#define XMP_INCLUDE_XMPFILES 1
#include "XMP.hpp"
#include "XMP.incl_cpp"

static std::string json(const std::string& s) {
    const char* hex = "0123456789abcdef";
    std::string out = "\"";
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { out += '\\'; out += char(c); }
        else if (c < 32) { out += "\\u00"; out += hex[c >> 4]; out += hex[c & 15]; }
        else out += char(c);
    }
    return out + '"';
}

int wmain(int argc, wchar_t** argv) {
    if (argc != 2) return 2;
    int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, argv[1], -1, nullptr, 0, nullptr, nullptr);
    if (!size) return 2;
    std::string filename(size, '\0');
    WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, argv[1], -1, filename.data(), size, nullptr, nullptr);
    bool core = false, files = false;
    int result = 0;
    try {
        core = SXMPMeta::Initialize();
        if (!core) throw std::runtime_error("XMPCore initialization failed");
        files = SXMPFiles::Initialize(XMP_OptionBits(0));
        if (!files) throw std::runtime_error("XMPFiles initialization failed");
        XMP_VersionInfo v{};
        SXMPFiles::GetVersionInfo(&v);
        std::cerr << v.message << '\n';
        SXMPFiles f;
        // Smart handlers only: no packet-scanning fallback that hides handler gaps.
        if (!f.OpenFile(filename.c_str(), kXMP_UnknownFile,
                        kXMPFiles_OpenForRead | kXMPFiles_OpenUseSmartHandler))
            throw std::runtime_error("No smart handler opened file");
        SXMPMeta meta;
        if (!f.GetXMP(&meta)) throw std::runtime_error("No XMP recovered");
        std::cout << '[';
        SXMPIterator it(meta, kXMP_IterJustLeafNodes);
        std::string ns, path, value;
        XMP_OptionBits options;
        bool first = true;
        while (it.Next(&ns, &path, &value, &options)) {
            if (!first) std::cout << ',';
            first = false;
            std::cout << "{\"namespace\":" << json(ns) << ",\"path\":" << json(path)
                      << ",\"value\":" << json(value) << ",\"options\":" << options << '}';
        }
        std::cout << "]\n";
        f.CloseFile();
    } catch (const XMP_Error& e) {
        std::cerr << "XMP error " << e.GetID() << ": " << e.GetErrMsg() << '\n'; result = 1;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n'; result = 1;
    }
    if (files) SXMPFiles::Terminate();
    if (core) SXMPMeta::Terminate();
    return result;
}
