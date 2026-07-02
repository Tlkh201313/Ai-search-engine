'use client';

import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  MapPin,
  Sun,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useState } from 'react';

interface Current {
  temp: number;
  code: number;
  wind: number;
}
interface Day {
  date: string;
  code: number;
  max: number;
  min: number;
}

const FALLBACK = { lat: 51.5074, lon: -0.1278, city: 'London' };

function iconFor(code: number): { Icon: LucideIcon; label: string } {
  if (code === 0) return { Icon: Sun, label: 'Clear' };
  if (code <= 2) return { Icon: CloudSun, label: 'Mostly clear' };
  if (code === 3) return { Icon: Cloud, label: 'Overcast' };
  if (code <= 48) return { Icon: CloudFog, label: 'Fog' };
  if (code <= 57) return { Icon: CloudDrizzle, label: 'Drizzle' };
  if (code <= 67 || (code >= 80 && code <= 82)) return { Icon: CloudRain, label: 'Rain' };
  if (code <= 77 || code === 85 || code === 86) return { Icon: CloudSnow, label: 'Snow' };
  return { Icon: CloudLightning, label: 'Thunderstorm' };
}

/** Live local weather via open-meteo (keyless, CORS-friendly). */
export function WeatherCard() {
  const [current, setCurrent] = useState<Current | null>(null);
  const [days, setDays] = useState<Day[]>([]);
  const [city, setCity] = useState<string>('');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async (lat: number, lon: number, fallbackCity: string) => {
      try {
        const url =
          `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
          '&current=temperature_2m,weather_code,wind_speed_10m' +
          '&daily=weather_code,temperature_2m_max,temperature_2m_min' +
          '&timezone=auto&forecast_days=5';
        const [weather, place] = await Promise.all([
          fetch(url).then((r) => r.json()),
          // Keyless reverse geocode; city name is nice-to-have, never blocking.
          fetch(
            `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=en`,
          )
            .then((r) => r.json())
            .catch(() => null),
        ]);
        if (cancelled) return;
        setCurrent({
          temp: Math.round(weather.current.temperature_2m),
          code: weather.current.weather_code,
          wind: Math.round(weather.current.wind_speed_10m),
        });
        setDays(
          (weather.daily.time as string[]).map((date: string, i: number) => ({
            date,
            code: weather.daily.weather_code[i],
            max: Math.round(weather.daily.temperature_2m_max[i]),
            min: Math.round(weather.daily.temperature_2m_min[i]),
          })),
        );
        setCity(place?.city || place?.locality || fallbackCity);
      } catch {
        if (!cancelled) setFailed(true);
      }
    };

    if (typeof navigator !== 'undefined' && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => load(pos.coords.latitude, pos.coords.longitude, 'Your area'),
        () => load(FALLBACK.lat, FALLBACK.lon, FALLBACK.city),
        { timeout: 5000, maximumAge: 600000 },
      );
    } else {
      load(FALLBACK.lat, FALLBACK.lon, FALLBACK.city);
    }
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) return null;

  const cond = current ? iconFor(current.code) : null;

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-sky-500 to-blue-700 p-4 text-white shadow-card">
      <div className="absolute -right-8 -top-10 h-36 w-36 rounded-full bg-white/10 blur-2xl" />
      <div className="relative">
        <div className="flex items-center gap-1.5 text-xs font-medium text-white/85">
          <MapPin className="h-3.5 w-3.5" />
          {city || 'Locating…'}
        </div>

        {current && cond ? (
          <>
            <div className="mt-2 flex items-center gap-3">
              <cond.Icon className="h-10 w-10 drop-shadow" strokeWidth={1.6} />
              <div>
                <div className="text-4xl font-semibold leading-none tracking-tight">
                  {current.temp}°
                </div>
                <div className="mt-1 text-xs text-white/85">
                  {cond.label} · wind {current.wind} km/h
                </div>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-5 gap-1 border-t border-white/20 pt-3">
              {days.map((d) => {
                const DayIcon = iconFor(d.code).Icon;
                return (
                  <div key={d.date} className="flex flex-col items-center gap-1">
                    <span className="text-[10px] font-medium uppercase text-white/75">
                      {new Date(d.date + 'T00:00:00').toLocaleDateString(undefined, {
                        weekday: 'short',
                      })}
                    </span>
                    <DayIcon className="h-4 w-4" />
                    <span className="text-[11px] font-medium">
                      {d.max}°<span className="text-white/60"> {d.min}°</span>
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <div className="mt-3 space-y-2">
            <div className="h-9 w-24 animate-pulse rounded bg-white/20" />
            <div className="h-3 w-36 animate-pulse rounded bg-white/15" />
          </div>
        )}
      </div>
    </div>
  );
}
