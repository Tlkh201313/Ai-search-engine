import { API_BASE } from './api';

export interface NewsItem {
  title: string;
  url: string;
  source: string;
  domain: string;
  summary: string;
  image: string | null;
  published_at: string | null;
}

export interface NewsResponse {
  category: string;
  categories: string[];
  items: NewsItem[];
}

export const NEWS_CATEGORIES: { key: string; label: string }[] = [
  { key: 'top', label: 'Top stories' },
  { key: 'world', label: 'World' },
  { key: 'tech', label: 'Tech' },
  { key: 'business', label: 'Business' },
  { key: 'science', label: 'Science' },
];

export async function fetchNews(category = 'top', limit = 24): Promise<NewsResponse> {
  const res = await fetch(
    `${API_BASE}/api/news?category=${encodeURIComponent(category)}&limit=${limit}`,
  );
  if (!res.ok) throw new Error(`news request failed (${res.status})`);
  return res.json() as Promise<NewsResponse>;
}
