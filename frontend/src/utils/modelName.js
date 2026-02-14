export function formatModelName(model) {
  if (typeof model !== 'string') return '';

  const trimmed = model.trim();
  if (!trimmed) return '';

  // Local models use "local/<id>" where <id> may itself be URI-like (hf://...).
  const withoutLocalPrefix = trimmed.startsWith('local/')
    ? trimmed.slice('local/'.length)
    : trimmed;

  // Preserve URI-style model ids (hf://..., ollama://..., file://...).
  if (withoutLocalPrefix.includes('://')) return withoutLocalPrefix;

  const slashIndex = withoutLocalPrefix.indexOf('/');
  if (slashIndex === -1) return withoutLocalPrefix;

  return withoutLocalPrefix.slice(slashIndex + 1) || withoutLocalPrefix;
}
