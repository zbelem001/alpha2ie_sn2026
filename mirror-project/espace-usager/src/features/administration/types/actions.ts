export type AdminActionRunner = (name: string, action: () => void | Promise<void>, success: string) => Promise<boolean>;
