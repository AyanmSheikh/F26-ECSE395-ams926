#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include "sdkconfig.h"

// Official QEMU Xtensa SIMCALL ABI, target/xtensa/xtensa-semi.c. ESP-IDF's
// esp_vfs_semihost_register uses an incompatible OpenOCD/ARM BREAK ABI.
// These calls only open/read/close the fixed relative frames.bin input.
namespace qemu_input {
inline int32_t syscall(int32_t operation, int32_t arg0 = 0, int32_t arg1 = 0, int32_t arg2 = 0) {
  register int32_t a2 asm("a2") = operation;
  register int32_t a3 asm("a3") = arg0;
  register int32_t a4 asm("a4") = arg1;
  register int32_t a5 asm("a5") = arg2;
  asm volatile("simcall" : "+a"(a2), "+a"(a3) : "a"(a4), "a"(a5) : "memory");
  return a2;
}

inline int open() {
  static const char path[] = "frames.bin";
#ifdef CONFIG_DEER_EVAL_HOST_WINDOWS
  constexpr int flags = 0x8000;  // Host Windows O_RDONLY | O_BINARY.
#else
  constexpr int flags = 0;       // Host POSIX O_RDONLY.
#endif
  return syscall(5, reinterpret_cast<int32_t>(path), flags, 0);
}

inline bool read_exact(int fd, void* data, size_t bytes) {
  auto* current = static_cast<uint8_t*>(data);
  while (bytes) {
    const auto request = static_cast<int32_t>(std::min<size_t>(bytes, 65536));
    const int32_t count = syscall(3, fd, reinterpret_cast<int32_t>(current), request);
    if (count <= 0 || count > request) return false;
    current += count;
    bytes -= count;
  }
  return true;
}

inline bool read_u32(int fd, uint32_t& value) {
  uint8_t raw[4];
  if (!read_exact(fd, raw, sizeof(raw))) return false;
  value = uint32_t(raw[0]) | (uint32_t(raw[1]) << 8) | (uint32_t(raw[2]) << 16) | (uint32_t(raw[3]) << 24);
  return true;
}

inline int close(int fd) { return syscall(6, fd); }

[[noreturn]] inline void exit(int status) {
  syscall(1, status);
  // A missing QEMU -semihosting option must never look like completion.
  __builtin_trap();
}
}  // namespace qemu_input
