/**
 * Tests for the useTheme hook.
 *
 * Covers:
 * - FE-15: window.matchMedia is guarded — hook does not throw when
 *          matchMedia is unavailable (SSR/test environments without matchMedia)
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTheme } from "@/hooks/use-theme";

// happy-dom does not implement window.matchMedia, so we define a controllable mock.
function setupMatchMedia(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: vi.fn().mockReturnValue({
      matches,
      media: "(prefers-color-scheme: dark)",
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

function removeMatchMedia() {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: undefined,
  });
}

afterEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
  vi.restoreAllMocks();
  // Reset matchMedia to undefined between tests to reflect happy-dom's default state
  removeMatchMedia();
});

// ── FE-15: window.matchMedia SSR guard ───────────────────────────────────────

describe("useTheme — matchMedia SSR guard", () => {
  it("does not throw when window.matchMedia is undefined", () => {
    // matchMedia is already undefined after afterEach — no localStorage either
    localStorage.clear();
    expect(() => renderHook(() => useTheme())).not.toThrow();
  });

  it("falls back to 'light' theme when matchMedia is unavailable and no localStorage value", () => {
    localStorage.clear();
    // matchMedia is undefined — the guard should catch this
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });

  it("reads 'dark' theme from localStorage without needing matchMedia", () => {
    localStorage.setItem("theme", "dark");
    // No matchMedia set up — localStorage branch returns early
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
  });

  it("reads 'light' theme from localStorage without needing matchMedia", () => {
    localStorage.setItem("theme", "light");
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });

  it("ignores invalid localStorage values and does not throw", () => {
    localStorage.setItem("theme", "invalid-value");
    expect(() => renderHook(() => useTheme())).not.toThrow();
  });
});

// ── Theme toggle ──────────────────────────────────────────────────────────────

describe("useTheme — toggle", () => {
  it("toggles from light to dark", () => {
    localStorage.setItem("theme", "light");
    const { result } = renderHook(() => useTheme());

    expect(result.current.theme).toBe("light");
    act(() => result.current.toggle());
    expect(result.current.theme).toBe("dark");
  });

  it("toggles from dark to light", () => {
    localStorage.setItem("theme", "dark");
    const { result } = renderHook(() => useTheme());

    expect(result.current.theme).toBe("dark");
    act(() => result.current.toggle());
    expect(result.current.theme).toBe("light");
  });

  it("persists the toggled theme to localStorage", () => {
    localStorage.setItem("theme", "light");
    const { result } = renderHook(() => useTheme());

    act(() => result.current.toggle());
    expect(localStorage.getItem("theme")).toBe("dark");
  });

  it("adds 'dark' class to documentElement when theme becomes dark", () => {
    localStorage.setItem("theme", "light");
    const { result } = renderHook(() => useTheme());

    act(() => result.current.toggle());
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("removes 'dark' class from documentElement when toggling back to light", () => {
    localStorage.setItem("theme", "dark");
    const { result } = renderHook(() => useTheme());

    // Dark class should be present after mount
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    act(() => result.current.toggle());
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});

// ── System preference via matchMedia ─────────────────────────────────────────

describe("useTheme — matchMedia system preference", () => {
  it("uses dark theme when system prefers dark and no localStorage value", () => {
    localStorage.clear();
    setupMatchMedia(true); // system prefers dark

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
  });

  it("uses light theme when system prefers light and no localStorage value", () => {
    localStorage.clear();
    setupMatchMedia(false); // system prefers light

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });

  it("localStorage value takes precedence over system preference", () => {
    localStorage.setItem("theme", "light");
    setupMatchMedia(true); // system says dark but localStorage says light

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });
});
