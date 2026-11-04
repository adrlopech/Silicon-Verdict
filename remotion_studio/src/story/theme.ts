export const CYAN = '#00F0FF';
export const BLUE = '#007AFF';
export const BG = '#07090E';
export const DARK_INK = '#06121C';
export const FONT = "'SF Pro Display', -apple-system, 'Helvetica Neue', Arial, sans-serif";

export type Pose = 'idle' | 'surprised' | 'point' | 'shrug' | 'think' | 'wave' | 'cheer';

export interface SceneSpec {
  start_frame: number;
  duration_frames: number;
  pose: Pose;
  flash?: boolean;
  vector?: VectorSpec | null;
}

export interface VectorSpec {
  type: 'counter' | 'bars' | 'gauge' | 'trio' | 'flow' | 'icon' | 'big_text';
  icon?: string;
  icon2?: string;
  icon3?: string;
  label?: string;
  label2?: string;
  label3?: string;
  value_from?: number;
  value_to?: number;
  a?: number;
  b?: number;
  text?: string;
}
