import { useEffect, useMemo, useRef, useState, type ElementRef, type KeyboardEvent } from 'react';
import { CalendarDays, ChevronDown } from 'lucide-react';
import {
  calendarDateKey,
  createReadingCalendar,
  readingColor,
  type DailyReadingProgress,
} from '../lib/readingCalendar';

const dayOffsets: Record<string, number> = {
  ArrowLeft: -7,
  ArrowRight: 7,
  ArrowUp: -1,
  ArrowDown: 1,
};

export function ReadingProgress({
  completed,
  total,
  dailyProgress,
  undatedCount,
  filtered,
  filterDate,
  onDateSelect,
  onUndatedSelect,
}: {
  completed: number;
  total: number;
  dailyProgress: ReadonlyMap<string, DailyReadingProgress>;
  undatedCount: number;
  filtered: boolean;
  filterDate: string | null;
  onDateSelect: (date: string) => void;
  onUndatedSelect: () => void;
}) {
  const today = calendarDateKey(new Date());
  const calendar = useMemo(
    () => createReadingCalendar(new Date(`${today}T00:00:00+08:00`)),
    [today],
  );
  const [selectedDate, setSelectedDate] = useState(filterDate ?? today);
  const [expanded, setExpanded] = useState(filterDate !== null);
  const scrollRef = useRef<ElementRef<'div'>>(null);
  const percentage = total === 0 ? 0 : (completed / total) * 100;
  const percentageLabel = percentage.toLocaleString('zh-CN', { maximumFractionDigits: 1 });
  const selectedProgress = dailyProgress.get(selectedDate);
  const formatPercentage = (value: number) =>
    value.toLocaleString('zh-CN', { style: 'percent', maximumFractionDigits: 1 });

  useEffect(() => {
    const scroller = scrollRef.current;
    if (scroller) scroller.scrollLeft = scroller.scrollWidth;
  }, [expanded]);

  const moveDay = (event: KeyboardEvent<ElementRef<'button'>>, date: string) => {
    const offset = dayOffsets[event.key];
    if (offset === undefined) return;
    event.preventDefault();
    const next = new Date(`${date}T12:00:00Z`);
    next.setUTCDate(next.getUTCDate() + offset);
    const nextDate = next.toISOString().slice(0, 10);
    if (nextDate >= calendar.firstDate && nextDate <= today) {
      scrollRef.current?.querySelector<ElementRef<'button'>>(`[data-date="${nextDate}"]`)?.focus();
    }
  };

  return (
    <section className="reading-overview" aria-label="阅读日历">
      <button
        type="button"
        className="reading-progress-heading calendar-toggle"
        aria-label={expanded ? '收起阅读日历' : '展开阅读日历'}
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="reading-progress-label">
          <span className="reading-progress-icon" aria-hidden="true">
            <CalendarDays size={18} />
          </span>
          <div>
            <p className="eyebrow">阅读日历</p>
            <p className="reading-progress-count" aria-live="polite" aria-atomic="true">
              <strong>{completed.toLocaleString('zh-CN')}</strong>
              <span> / {total.toLocaleString('zh-CN')} 篇已读</span>
            </p>
          </div>
        </div>
        <span className="calendar-toggle-right">
          <span className="reading-progress-percentage">{percentageLabel}%</span>
          <ChevronDown
            size={17}
            className={expanded ? 'calendar-chevron expanded' : 'calendar-chevron'}
          />
        </span>
      </button>

      {expanded ? (
        <>
          <div className="reading-calendar-summary">
            <span>按 Online 日期 · 颜色表示当天文章的已读比例</span>
            <span className="reading-calendar-period">
              {calendar.firstDate.replace(/-/g, '.')} — {calendar.lastDate.replace(/-/g, '.')}
            </span>
          </div>
          <div className="reading-calendar-scroll" ref={scrollRef}>
            <div
              className="reading-calendar"
              role="group"
              aria-label="每日阅读热图，使用方向键切换日期"
            >
              <div className="reading-calendar-weekdays" aria-hidden="true">
                <span />
                {['一', '', '三', '', '五', '', '日'].map((label, index) => (
                  <span key={index}>{label}</span>
                ))}
              </div>
              <div className="reading-calendar-weeks">
                {calendar.weeks.map((week) => (
                  <div className="reading-calendar-week" key={week[0].date}>
                    <span className="reading-calendar-month" aria-hidden="true">
                      {week.find((day) => day.monthLabel)?.monthLabel}
                    </span>
                    {week.map((day) => {
                      if (!day.inRange) {
                        return <span className="reading-calendar-blank" key={day.date} />;
                      }
                      const progress = dailyProgress.get(day.date);
                      const ratio = progress ? progress.completed / progress.total : null;
                      const label = progress
                        ? `${day.label}：Online 发表 ${progress.total} 篇，已读 ${progress.completed} 篇（${formatPercentage(ratio!)}）`
                        : `${day.label}：暂无 Online 发表的文章`;
                      return (
                        <button
                          key={day.date}
                          type="button"
                          className="reading-calendar-day"
                          style={
                            ratio === null ? undefined : { backgroundColor: readingColor(ratio) }
                          }
                          data-empty={progress ? undefined : true}
                          data-date={day.date}
                          aria-label={label}
                          title={label}
                          aria-current={day.date === today ? 'date' : undefined}
                          aria-pressed={filterDate === day.date}
                          tabIndex={selectedDate === day.date ? 0 : -1}
                          onClick={() => {
                            setSelectedDate(day.date);
                            onDateSelect(day.date);
                          }}
                          onFocus={() => setSelectedDate(day.date)}
                          onKeyDown={(event) => moveDay(event, day.date)}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="reading-calendar-caption">
            <p className="reading-calendar-selection" aria-live="polite" aria-atomic="true">
              {selectedDate} ·{' '}
              {selectedProgress
                ? `${selectedProgress.completed} / ${selectedProgress.total} 篇已读（${formatPercentage(selectedProgress.completed / selectedProgress.total)}）`
                : '暂无 Online 发表的文章'}
            </p>
            <div
              className="reading-calendar-legend"
              aria-label="颜色从浅到深表示已读比例从0%到100%，灰色表示暂无Online发表的文章"
            >
              <span className="reading-calendar-swatch reading-calendar-no-articles" />
              <span>无文章</span>
              <span>0%</span>
              {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
                <span
                  className="reading-calendar-swatch"
                  style={{ backgroundColor: readingColor(ratio) }}
                  title={formatPercentage(ratio)}
                  key={ratio}
                />
              ))}
              <span>100%</span>
            </div>
          </div>
        </>
      ) : null}
      {undatedCount > 0 ? (
        <p className="reading-calendar-note">
          {undatedCount} 篇尚未获取 Online 日期，暂未计入日历。
          <button type="button" onClick={onUndatedSelect}>
            查看这些文章
          </button>
        </p>
      ) : null}
      <div className="reading-progress-footer">
        <span>
          {filtered ? '当前筛选范围' : '全部文章'} · {total - completed} 篇未读
        </span>
        <span>{expanded ? '点击日期，查看当天文章' : '展开日历，按日期筛选'}</span>
      </div>
    </section>
  );
}
