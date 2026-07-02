'use client';

import { TrendingDown, TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';

const COINS = [
  { id: 'bitcoin', symbol: 'BTC', name: 'Bitcoin' },
  { id: 'ethereum', symbol: 'ETH', name: 'Ethereum' },
  { id: 'solana', symbol: 'SOL', name: 'Solana' },
  { id: 'dogecoin', symbol: 'DOGE', name: 'Dogecoin' },
] as const;

interface Row {
  symbol: string;
  name: string;
  price: number;
  change: number;
}

function formatPrice(value: number): string {
  if (value >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (value >= 1) return value.toFixed(2);
  return value.toFixed(4);
}

/** Live crypto markets via CoinGecko (keyless, CORS-friendly). */
export function MarketsCard() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const ids = COINS.map((c) => c.id).join(',');
    fetch(
      `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true`,
    )
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data) => {
        if (cancelled) return;
        setRows(
          COINS.filter((c) => data[c.id]?.usd != null).map((c) => ({
            symbol: c.symbol,
            name: c.name,
            price: data[c.id].usd,
            change: data[c.id].usd_24h_change ?? 0,
          })),
        );
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) return null;

  return (
    <div className="card p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">Markets</h3>
        <span className="text-[10px] font-medium uppercase tracking-wide text-faint">
          Crypto · 24h
        </span>
      </div>

      {rows ? (
        <div className="space-y-2.5">
          {rows.map((row) => {
            const up = row.change >= 0;
            return (
              <div key={row.symbol} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-9 items-center justify-center rounded-md bg-ink/5 text-[10px] font-bold text-muted">
                    {row.symbol}
                  </span>
                  <span className="text-[13px] text-ink">{row.name}</span>
                </div>
                <div className="text-right">
                  <div className="text-[13px] font-medium tabular-nums text-ink">
                    ${formatPrice(row.price)}
                  </div>
                  <div
                    className={`flex items-center justify-end gap-0.5 text-[11px] font-medium tabular-nums ${
                      up
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}
                  >
                    {up ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    {up ? '+' : ''}
                    {row.change.toFixed(2)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="space-y-2.5">
          {COINS.map((c) => (
            <div key={c.id} className="skeleton h-8 rounded-lg" />
          ))}
        </div>
      )}
    </div>
  );
}
