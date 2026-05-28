export type ModelEndpointValidation = {
  isValid: boolean;
  message: string;
  reason: string | null;
};

export function validateLocalModelEndpoint(endpoint: string): ModelEndpointValidation {
  try {
    const parsed = new URL(endpoint);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return {
        isValid: false,
        message: "Endpoint must use http or https.",
        reason: "invalid_scheme",
      };
    }
    if (!["127.0.0.1", "localhost", "::1"].includes(parsed.hostname)) {
      return {
        isValid: false,
        message: "Remote model endpoints are blocked.",
        reason: "remote_endpoint",
      };
    }
    if (parsed.username || parsed.password || parsed.pathname !== "/" || parsed.search || parsed.hash) {
      return {
        isValid: false,
        message: "Endpoint must not include credentials, paths, queries, or fragments.",
        reason: "invalid_shape",
      };
    }
    return {
      isValid: true,
      message: "Ollama endpoint localhost.",
      reason: null,
    };
  } catch {
    return {
      isValid: false,
      message: "Model endpoint must be a valid local URL.",
      reason: "invalid_url",
    };
  }
}

export function parseFileWatchRoots(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(/\r?\n/)
        .map((entry) => entry.trim())
        .filter(Boolean),
    ),
  );
}
