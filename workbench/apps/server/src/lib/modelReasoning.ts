export const thinkingLevels = ["off", "minimal", "low", "medium", "high", "xhigh", "max"] as const;
export const defaultThinkingLevels = ["low", "medium", "high"] as const;

export type ThinkingLevel = typeof thinkingLevels[number];
export type ReasoningEfforts = false | Partial<Record<ThinkingLevel, string | null>>;
