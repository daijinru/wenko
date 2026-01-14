/**
 * @file Define the type of the global window object.
 * @module types/window
 */
interface Window {
  /**
   * Asteroids game class.
   * @type {any}
   */
  Asteroids: any;
   /**
   * Asteroids game player array.
   * @type {any[]}
   */
  ASTEROIDSPLAYERS: any[];
  /**
   * Function to initialize the Live2D widget.
   * @type {(config: Config) => void}
   */
  initWidget: (config: Config) => void;

  electronAPI: {
    send(channel: string, ...args: any[]): void;
    invoke?(channel: string, ...args: any[]): Promise<any>;
    // 根据你调用 electronAPI 的具体接口补充声明
  };
}
