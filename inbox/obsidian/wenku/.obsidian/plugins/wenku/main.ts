import {
	App, Editor, MarkdownView, Modal,
	Notice, Plugin, PluginSettingTab, Setting,
	request,
} from 'obsidian';

interface SearchResult {
  id: string;
  content: string;
	hasEmbedding?: boolean; // 标识是否用于下一步 Embedding
}
// Remember to rename these classes and interfaces!

interface MyPluginSettings {
	mySetting: string;
}

const DEFAULT_SETTINGS: MyPluginSettings = {
	mySetting: 'default'
}

export default class MyPlugin extends Plugin {
	settings: MyPluginSettings;

  private collectHighlights(): string[] {
    const activeView = this.app.workspace.getActiveViewOfType(MarkdownView); 
    if (!activeView || !activeView.editor)  return [];
 
    const editor = activeView.editor; 
    const content = editor.getValue(); 
    const highlights: string[] = [];
 
    // 正则匹配 Markdown 高亮语法 ==高亮内容== 
    const highlightRegex = /==([^=]+)==/g;
    let match;
    while ((match = highlightRegex.exec(content))  !== null) {
      highlights.push(match[1]);  // 捕获组内容（不含==符号）
    }
 
    return highlights;
  }

	private vectorCache = new Map<string, SearchResult>();
	private vectorCacheGet(inputText: string): string {
		if (this.vectorCache.has(inputText)) {
			return this.vectorCache.get(inputText)!.content;
		}
		return "";
	}
  private async diffSearchVector(inputText: string): Promise<SearchResult | void> {
    try {
			// 检查缓存
			console.info("正在检查缓存内容:", this.vectorCache);
			const cachedContent = this.vectorCacheGet(inputText);
			if (cachedContent) {
				return Promise.resolve({ id: "", content: cachedContent, hasEmbedding: true });
			}

      const response = await request({ 
        url: 'http://localhost:8080/search',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({  text: inputText })
      });
 
      const results: SearchResult[] = JSON.parse(response); 
      if (!Array.isArray(results))  throw new Error("无效的API响应结构");
 
			const matchResult = results.find(item => {
				// 远程内容都要缓存
				this.vectorCache.set(item.content, item);
				// 只要有一个匹配就返回
				return item.content === inputText;
			})

			if (matchResult) {
				console.info(`ID ${matchResult.id} 内容匹配:\n${matchResult.content}`);
				return {...matchResult, hasEmbedding: true };
			} else {
				console.info("没有找到匹配的内容：", inputText);
				return {id: '', content: inputText, hasEmbedding: false };
			}
 
    } catch (error) {
      new Notice(`API请求失败: ${error instanceof Error ? error.message  : String(error)}`);
      console.error("API 错误:", error);
    }
  }

	async onload() {
		await this.loadSettings();

    this.registerEvent( 
      this.app.workspace.on("file-menu",  (menu, file) => {
        menu.addItem((item)  => {
          item 
            .setTitle("对高亮 Embedding")
            .setIcon("highlighter")
            .onClick(async () => {
              console.log(" 点击了右键菜单按钮", file);
							const highlights = this.collectHighlights()
							if (highlights.length === 0) {
								new Notice("没有找到高亮内容");
								return;
							}
							new Notice(`已收集高亮内容: ${highlights.join(", ")}`);

							// 使用 Promise.all 来并行处理每个高亮
							const reqs = highlights.map((text) => {
								return this.diffSearchVector(text)
							});
							Promise.all(reqs)
							  .then((results) => {
								console.info("所有请求结果:", results);
								// 处理所有结果
								results.forEach((result) => {
									if (result && result.hasEmbedding) {
										new Notice(`${result.content} 已存在无需Embedding`);
									} else if (result && !result.hasEmbedding) {
										new Notice(`${result.content} 开始进行Embedding`);
									}
								});
							})
							.catch((error) => {
								console.error("处理请求时出错:", error);
								new Notice(`处理请求时出错: ${error instanceof Error ? error.message : String(error)}`)
							});
            });
        });
      })
    );

		// This creates an icon in the left ribbon.
		// const ribbonIconEl = this.addRibbonIcon('dice', 'Obsidian Wenku', (evt: MouseEvent) => {
		// 	new Notice('Hi World!');
		// });
		// Perform additional things with the ribbon
		// ribbonIconEl.addClass('my-plugin-ribbon-class');

		// This adds a status bar item to the bottom of the app. Does not work on mobile apps.
		const statusBarItemEl = this.addStatusBarItem();
		statusBarItemEl.setText('Status Bar Text');

		// This adds a simple command that can be triggered anywhere
		this.addCommand({
			id: 'open-sample-modal-simple',
			name: 'Open sample modal (simple)',
			callback: () => {
				new SampleModal(this.app).open();
			}
		});
		// This adds an editor command that can perform some operation on the current editor instance
		this.addCommand({
			id: 'sample-editor-command',
			name: 'Sample editor command',
			editorCallback: (editor: Editor, view: MarkdownView) => {
				console.log(editor.getSelection());
				editor.replaceSelection('Sample Editor Command');
			}
		});
		// This adds a complex command that can check whether the current state of the app allows execution of the command
		this.addCommand({
			id: 'open-sample-modal-complex',
			name: 'Open sample modal (complex)',
			checkCallback: (checking: boolean) => {
				// Conditions to check
				const markdownView = this.app.workspace.getActiveViewOfType(MarkdownView);
				if (markdownView) {
					// If checking is true, we're simply "checking" if the command can be run.
					// If checking is false, then we want to actually perform the operation.
					if (!checking) {
						new SampleModal(this.app).open();
					}

					// This command will only show up in Command Palette when the check function returns true
					return true;
				}
			}
		});

		// This adds a settings tab so the user can configure various aspects of the plugin
		this.addSettingTab(new SampleSettingTab(this.app, this));

		// If the plugin hooks up any global DOM events (on parts of the app that doesn't belong to this plugin)
		// Using this function will automatically remove the event listener when this plugin is disabled.
		this.registerDomEvent(document, 'click', (evt: MouseEvent) => {
			// console.log('click', evt);
		});

		// When registering intervals, this function will automatically clear the interval when the plugin is disabled.
		this.registerInterval(window.setInterval(() => console.log('setInterval'), 5 * 60 * 1000));
	}

	onunload() {

	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}
}

class SampleModal extends Modal {
	constructor(app: App) {
		super(app);
	}

	onOpen() {
		const {contentEl} = this;
		contentEl.setText('Woah!');
	}

	onClose() {
		const {contentEl} = this;
		contentEl.empty();
	}
}

class SampleSettingTab extends PluginSettingTab {
	plugin: MyPlugin;

	constructor(app: App, plugin: MyPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const {containerEl} = this;

		containerEl.empty();

		new Setting(containerEl)
			.setName('Setting #1')
			.setDesc('It\'s a secret')
			.addText(text => text
				.setPlaceholder('Enter your secret')
				.setValue(this.plugin.settings.mySetting)
				.onChange(async (value) => {
					this.plugin.settings.mySetting = value;
					await this.plugin.saveSettings();
				}));
	}
}
