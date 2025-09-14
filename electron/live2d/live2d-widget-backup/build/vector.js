export const generate = (input) => {
    const { texts, original = '', } = input;
    return new Promise((resolve, reject) => {
        fetch("http://localhost:8080/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                texts,
                original,
            }),
        })
            .then((res) => res.json())
            .then((res) => {
            if (res.id) {
                const text = `😊 Generated [id ${res.id}]`;
                resolve(text);
            }
            else {
                const text = '😂 Save Text failed';
                reject(text);
            }
        })
            .catch(err => {
            const text = '😂 Save Text error: ' + err;
            reject(text);
        });
    });
};
export const search = (input) => {
    return new Promise((resolve, reject) => {
        fetch("http://localhost:8080/search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                texts: input,
            }),
        })
            .then((res) => res.json())
            .then((data) => {
            resolve(data);
        })
            .catch(err => {
            const text = '😂 Search error: ' + err;
            reject(text);
        });
    });
};
