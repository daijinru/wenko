import { useState, useEffect } from 'react';
import './styles/globals.css';

interface PlanReminder {
  id: string;
  title: string;
  description?: string;
  target_time: string;
  repeat_type: string;
}

type SnoozeOption = { label: string; minutes: number };

const SNOOZE_OPTIONS: SnoozeOption[] = [
  { label: '5 分钟', minutes: 5 },
  { label: '15 分钟', minutes: 15 },
  { label: '1 小时', minutes: 60 },
];

export default function App() {
  const [reminder, setReminder] = useState<PlanReminder | null>(null);
  const [showSnooze, setShowSnooze] = useState(false);
  const [isActing, setIsActing] = useState(false);

  useEffect(() => {
    if (!window.electronAPI?.on) return;

    // Listen for data
    const unsubscribe = window.electronAPI.on('reminder:data', (data: PlanReminder) => {
      console.log('[Reminder] Received data:', data);
      setReminder(data);
    });

    // Request data from main process
    window.electronAPI.invoke('reminder:get-data').then((data: PlanReminder | null) => {
      if (data) {
        console.log('[Reminder] Got data via invoke:', data);
        setReminder(data);
      }
    }).catch((err: Error) => {
      console.error('[Reminder] Failed to get data:', err);
    });

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, []);

  if (!reminder) {
    return (
      <div className="theme-classic h-screen flex items-center justify-center">
        <span className="text-xs">加载中...</span>
      </div>
    );
  }

  const rawTime = reminder.target_time;
  const normalizedTime = rawTime.endsWith('Z') || rawTime.includes('+') ? rawTime : rawTime + 'Z';
  const targetTime = new Date(normalizedTime);
  const timeStr = targetTime.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  const dateStr = targetTime.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });

  const handleComplete = async () => {
    if (isActing) return;
    setIsActing(true);
    try {
      await window.electronAPI?.invoke('reminder:complete', reminder.id);
    } catch (e) {
      console.error('[Reminder] Complete error:', e);
    }
  };

  const handleSnooze = async (minutes: number) => {
    if (isActing) return;
    setIsActing(true);
    try {
      await window.electronAPI?.invoke('reminder:snooze', {
        planId: reminder.id,
        snoozeMinutes: minutes,
      });
    } catch (e) {
      console.error('[Reminder] Snooze error:', e);
    }
  };

  const handleDismiss = async () => {
    if (isActing) return;
    setIsActing(true);
    try {
      await window.electronAPI?.invoke('reminder:dismiss', reminder.id);
    } catch (e) {
      console.error('[Reminder] Dismiss error:', e);
    }
  };

  return (
    <div className="theme-classic h-screen flex flex-col">
      <div className="window active flex-1 flex flex-col">
        {/* Title bar */}
        <header className="window-draggable bg-classic-title border-b border-border !p-[6px] !mb-[6px] flex justify-between items-center">
          <h1 className="flex-1 text-center text-xs font-bold">计划提醒</h1>
        </header>

        {/* Content */}
        <div className="!p-[12px] window-body flex-1 flex flex-col">
          {/* Reminder card */}
          <div className="reminder-gradient text-white rounded-lg !p-[16px] !mb-[12px]">
            <div className="flex items-center gap-2 !mb-[8px]">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2zm-2 1H8v-6c0-2.48 1.51-4.5 4-4.5s4 2.02 4 4.5v6z"/>
              </svg>
              <span className="font-bold text-sm">计划提醒</span>
              <span className="opacity-80 text-xs ml-auto">{dateStr} {timeStr}</span>
            </div>

            <div className="text-base font-medium !mb-[4px]">
              {reminder.title}
            </div>

            {reminder.description && (
              <div className="text-xs opacity-90 !mb-[4px]">
                {reminder.description}
              </div>
            )}

            {reminder.repeat_type && reminder.repeat_type !== 'none' && (
              <div className="text-xs opacity-70">
                重复: {reminder.repeat_type}
              </div>
            )}
          </div>

          {/* Snooze options */}
          {showSnooze && (
            <div className="flex gap-2 !mb-[12px]">
              {SNOOZE_OPTIONS.map((opt) => (
                <button
                  key={opt.minutes}
                  disabled={isActing}
                  onClick={() => handleSnooze(opt.minutes)}
                  className="window-not-draggable flex-1 !p-[6px] text-xs border border-border rounded bg-white hover:bg-gray-100 disabled:opacity-50 cursor-pointer"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-auto flex gap-2">
            <button
              disabled={isActing}
              onClick={handleComplete}
              className="window-not-draggable flex-1 !p-[8px] text-xs font-medium border-none rounded reminder-gradient text-white disabled:opacity-50 cursor-pointer"
            >
              完成
            </button>
            <button
              disabled={isActing}
              onClick={() => setShowSnooze(!showSnooze)}
              className="window-not-draggable flex-1 !p-[8px] text-xs font-medium border border-border rounded bg-white hover:bg-gray-100 disabled:opacity-50 cursor-pointer"
            >
              稍后提醒
            </button>
            <button
              disabled={isActing}
              onClick={handleDismiss}
              className="window-not-draggable !p-[8px] !px-[12px] text-xs border border-border rounded bg-white hover:bg-gray-100 disabled:opacity-50 cursor-pointer"
            >
              取消
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
