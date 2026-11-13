// Types for the host-provided App SDK (resolved at runtime through the import map).
// Shapes follow kiro.dev/docs/crew/apps/sdk/ and the Crew 0.12.2 host bundle.
declare module '@kirocrew/app-sdk' {
  export interface AppApiClient {
    get<T = unknown>(path: string, opts?: { signal?: AbortSignal }): Promise<T>
    post<T = unknown>(path: string, body?: unknown, opts?: { signal?: AbortSignal }): Promise<T>
    put<T = unknown>(path: string, body?: unknown, opts?: { signal?: AbortSignal }): Promise<T>
    patch<T = unknown>(path: string, body?: unknown, opts?: { signal?: AbortSignal }): Promise<T>
    del<T = unknown>(path: string, opts?: { signal?: AbortSignal }): Promise<T>
  }
  export function useAppApi(): AppApiClient
  export function useNotify(): (text: string, opts?: Record<string, unknown>) => void
  export function useChatLauncher(): {
    openChat(opts: { agent?: string; message?: string; autoSend?: boolean; slotKey?: string }): void
  }
}
