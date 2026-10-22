/** Resolve API base paths while keeping Vite development traffic on its proxy. */
export function resolveApiBase(isDevelopment, configuredUrl) {
  if (isDevelopment) return '/api'

  const trimmed = (configuredUrl ?? '').trim().replace(/\/+$/, '')
  const originOrBase = trimmed.replace(/\/api$/i, '')
  return originOrBase ? `${originOrBase}/api` : '/api'
}
