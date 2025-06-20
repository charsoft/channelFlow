export function sanitizeTitleForFilename(title: string): string {
  if (!title) return 'video_clip';
  const sanitized = title.replace(/[*:"<>?|/\\.]/g, '').replace(/\s+/g, '_').toLowerCase();
  return (sanitized.substring(0, 80) || 'video_clip');
} 