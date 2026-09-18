export class UnauthorizedError extends Error {}

// Like fetch, but a 401 (expired or missing session) is reported as UnauthorizedError.
export const apiFetch = async (path: string, options?: RequestInit) => {
  const response = await fetch(path, options);
  if (response.status === 401) {
    throw new UnauthorizedError("Authentication required.");
  }
  return response;
};
