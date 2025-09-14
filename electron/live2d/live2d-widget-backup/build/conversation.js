import { fetchEventSource } from "https://esm.sh/@microsoft/fetch-event-source";
import { generateMsgId } from "./utils.js";
import { generate, search } from "./vector.js";
export const getKanbanDaily = (text, callback, loadingCallback, doneCallback) => {
    let interval = setInterval(() => {
        loadingCallback && loadingCallback('.');
    }, 1000);
    let out = '';
    setTimeout(() => {
        fetchEventSource('http://localhost:8080/task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: generateMsgId(),
                text,
            }),
            onopen: (res) => {
                console.log('open', res);
                if (res.ok)
                    return Promise.resolve();
            },
            onmessage: (line) => {
                if (interval) {
                    clearInterval(interval);
                    interval = null;
                }
                try {
                    if (line.event !== 'text')
                        return;
                    const data = JSON.parse(line.data);
                    if (data.type !== 'text')
                        return;
                    const payload = data.payload;
                    if (payload.type !== 'text')
                        return;
                    out += payload.content;
                    callback(payload.content);
                }
                catch (error) {
                    console.error(error);
                }
            },
            onclose: () => {
                doneCallback && doneCallback();
            },
            onerror: (err) => {
                console.log('error', err);
            },
        });
    }, 1500);
};
export const getWeightedTexts = (text) => {
    return [
        { Text: text, Weight: 0.6 },
        { Text: document.title, Weight: 0.2 },
        { Text: location.href, Weight: 0.1 },
        { Text: new Date().getTime().toString(), Weight: 0.1 },
    ];
};
export const getSearch = (text, callback, loadingCallback) => {
    let interval = setInterval(() => {
        loadingCallback && loadingCallback('.');
    }, 1000);
    const weightedTexts = getWeightedTexts(text);
    generate(weightedTexts)
        .then(res => {
        clearInterval(interval);
        callback(res);
    })
        .catch((err) => {
        console.error('❌ 生成向量失败', err);
        clearInterval(interval);
        callback('😂 Save Text error');
    });
};
export const saveHightlightText = (text, callback, loadingCallback) => {
    let interval = setInterval(() => {
        loadingCallback && loadingCallback('.');
    }, 1000);
    const weightedTexts = getWeightedTexts(text);
    fetch("http://localhost:8080/generate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            texts: weightedTexts,
        }),
    })
        .then((res) => res.json())
        .then((res) => {
        interval && clearInterval(interval);
        if (res.id) {
            const text = `😊 Generated [id ${res.id}]`;
            callback(text);
        }
        else {
            callback('😂 Save Text failed');
        }
    })
        .catch(err => {
        console.error('❌ 生成向量失败', err);
        interval && clearInterval(interval);
        callback('😂 Save Text error');
    });
};
export const saveDaily = (callback, loadingCallback) => {
    let interval = setInterval(() => {
        loadingCallback && loadingCallback('.');
    }, 1000);
    const weightedTexts = [
        { Text: document.title, Weight: 0.3 },
        { Text: location.href, Weight: 0.4 },
        { Text: new Date().getTime().toString(), Weight: 0.3 },
    ];
    const original = {
        title: document.title,
        url: location.href,
        time: new Date().getTime().toString(),
    };
    generate({
        texts: weightedTexts,
        original: JSON.stringify(original),
    })
        .then(res => {
        clearInterval(interval);
        callback(res);
    })
        .catch((err) => {
        console.error('❌ 保存用户行为失败', err);
        clearInterval(interval);
        callback('😂 Save User Behavior error');
    });
};
export const getDaily = (callback, loadingCallback, doneCallback) => {
    let interval = setInterval(() => {
        loadingCallback && loadingCallback('.');
    }, 1000);
    const weightedTexts = [
        { Text: document.title, Weight: 0.3 },
        { Text: location.href, Weight: 0.4 },
        { Text: new Date().getTime().toString(), Weight: 0.3 },
    ];
    search(weightedTexts)
        .then(res => {
        clearInterval(interval);
        if (!Array.isArray(res))
            return;
        const texts = res.map(item => {
            const arr = item.content.split('-$-$');
            return {
                title: arr[0].replace(/\(weight-assign:.*?\)/, ''),
                url: arr[1].replace(/\(weight-assign:.*?\)/, ''),
                time: arr[2].replace(/\(weight-assign:.*?\)/, ''),
            };
        });
        const content = document.body.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').substring(0, 500);
        const userInput = `
${texts.map(item => {
            return `
    用户在 时间：${item.time} 访问了网页：标题： ${item.title}，地址：(${item.url})，
    `;
        }).join('\n')}
当前访问内容：${content}
`;
        console.log('📝 userInput', userInput);
        fetchEventSource('http://localhost:8080/task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: generateMsgId(),
                text: userInput,
            }),
            onopen: (res) => {
                console.log('open', res);
                if (res.ok)
                    return Promise.resolve();
            },
            onmessage: (line) => {
                if (interval) {
                    clearInterval(interval);
                    interval = null;
                }
                try {
                    if (line.event !== 'text')
                        return;
                    const data = JSON.parse(line.data);
                    if (data.type !== 'text')
                        return;
                    const payload = data.payload;
                    if (payload.type !== 'text')
                        return;
                    callback(payload.content);
                }
                catch (error) {
                    console.error(error);
                }
            },
            onclose: () => {
                doneCallback && doneCallback();
            },
            onerror: (err) => {
                console.log('error', err);
            },
        });
    })
        .catch((err) => {
        console.error('❌ 查询用户行为失败', err);
        clearInterval(interval);
        callback('😂 Search User Behavior error');
    });
};
