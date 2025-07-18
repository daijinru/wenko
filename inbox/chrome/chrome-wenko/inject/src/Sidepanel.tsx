import { useState, useEffect, useRef } from 'react'
import { pick } from 'lodash-es'

import { SmileOutlined, BlockOutlined, ShareAltOutlined } from '@ant-design/icons'

import './Sidepanel.css'

// WENKO 注入脚本
window['WENKO_ROOT_ID'] = 'WENKO__CONTAINER-ROOT'
window['WENKO_ROOT'] = {
  console: {
    info: (...args) => {
      console.info('%c<wenko>%c', 'background: green; color: white; font-weight: bold; font-size: 16px; text-transform: uppercase;', 'color: inherit;', ...args)
    },
    error: (...args) => {
      console.info('%c<wenko>%c', 'background: red; color: white; font-weight: bold; font-size: 16px; text-transform: uppercase;', 'color: inherit;', ...args)
    },
  }
}
// WENKO 注入脚本
const CONSOLE = window['WENKO_ROOT'].console

/**
 * 带权重的文本结构体
 * ```javascript
 * { Text: selectedText, Weight: 0.6 },                       // 高亮文本为核心，权重最高
 * { Text: document.title, Weight: 0.15 },                   // 网页标题，体现页面主题
 * { Text: location.href, Weight: 0.15 },                    // URL，提供上下文来源
 * { Text: document.body.innerText.slice(0, 500), Weight: 0.1 }, // 网页正文首500字符，提供部分上下文
 * ```
 */
type WeightedText = {
	Text: string
	Weight: number
}

const Sidepanel = (props) => {
  const [selectedText, setSelectedText] = useState('')
  const refTexts = useRef<Record<string, string>>([] as any)
  const [matchResults, setMatchResults] = useState([])
  const hightlightId = useRef('')
  const [savingText, setSavingText] = useState('Welcome to Wenko!')
  useEffect(() => {
    // 接收后台传递的文本 
    const text = props.text.split('_')[0]; // 仅获取文本部分
    setSelectedText(text);
    refTexts.current = {...pick(props, ['url', 'title', 'body']), ...{text}};
    const id = props.text.split('_')[1]
    hightlightId.current = id; // 更新高亮ID
  }, [])

  useEffect(() => {
    if (selectedText) {
      setMatchResults([])

      // 请求 http://localhost:8080/search 接口，请求体 text
      // 设置带权重的文本结构体
      const weightedTexts: WeightedText[] = [
        { Text: refTexts.current.text, Weight: 0.6 },
        { Text: refTexts.current.title, Weight: 0.15 },
        { Text: refTexts.current.url, Weight: 0.15 },
        { Text: refTexts.current.body, Weight: 0.1 },
      ]
      CONSOLE.info('获得权重文本：', weightedTexts)
      setSavingText('Searching...' + selectedText.slice(0, 10) + '...')
      fetch("http://localhost:8080/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          texts: weightedTexts,
        }),
      })
        .then((res) => res.json())
        .then(async data => {
          setMatchResults(data)

          const promises = data.map(async item => {
            const res = await fetch('http://localhost:8080/compare', {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                texts: weightedTexts,
                id: item.id
              }),
            })
            const parsed = await res.json()
            return parsed.result
          })
          setSavingText('Comparing...' + selectedText.slice(0, 22))
          const finalRes = await Promise.all(promises)
          const matched = finalRes.some(fr => fr)
          if (matched) {
            const text = `Matched <${finalRes.join(', ')}>, No Generated`
            setSavingText(text)
            return
          }
          // const matchResult = data.find(item => item.content === selectedText)
          // if (matchResult && matchResult.content) return
          CONSOLE.info('❌ 未找到匹配结果，开始生成向量')
          setSavingText('Generating...' + selectedText.slice(0, 22))
          // 请求 http://localhost:8080/generate 接口，请求体 text，返回的 id
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
              if (res.id) {
                const text = `Generated <id ${res.id}>`
                setSavingText(text)
              }
            })
            .catch(err => {
              CONSOLE.error('❌ 生成向量失败', err)
              setSavingText('❌ 生成向量失败')
            })
        })
    }
  }, [selectedText])

  return (
    <main className='bg-[rgba(58,123,186,1)] pt-16px'>
      {
        savingText && <div className='text-left text-14px text-[#fff] pl-16px whitespace-nowrap truncate'><SmileOutlined /> {savingText}</div>
      }

      <div
        className='w-full rounded-lg px-4 py-6 shadow-inner border border-[rgba(58,123,186,0.3)]'
      >
        <div className='flex flex-col gap-6'>
          <div
            className='bg-white border border-[rgba(58,123,186,0.3)] rounded-md p-4 shadow-sm hover:shadow-md transition-shadow duration-300'
          >
            <blockquote
              className='text-14px text-[#000] font-bold select-text leading-relaxed pl-16px'
              style={{
                boxShadow: 'inset 3px 0 0 0 #242424',
              }}
            >
              <BlockOutlined /> {selectedText}
            </blockquote>
          </div>
          {
            matchResults.map((item, key) => {
              return (
                <div
                  key={key}
                  className='bg-white border border-[rgba(58,123,186,0.3)] rounded-md p-4 shadow-sm hover:shadow-md transition-shadow duration-300'
                >
                  <p className='flex flex-col gap-3 text-12px text-[rgba(0,0,0,0.88)] leading-relaxed break-words font-serif'>
                    <span className='mb-2 text-14px text-[#000] font-bold border-b border-[rgba(58,123,186,0.3)] pb-1 select-text'>
                      <ShareAltOutlined /> 线索{key + 1}
                    </span>
                    {
                      item.content.split('$-$').map((part, index) => {
                        if (index === 0) {
                          return <span key={index} className='select-text'>{part}</span>
                        }
                        if (index === 1) {
                          return (
                            <span
                              key={index}
                              className='m-0 mx-[0.2em] px-[0.4em] py-[0.4em] pb-[0.1em] text-[90%] font-mono bg-[rgba(150,150,150,0.06)] border border-[rgba(100, 100, 100, 0.2)] border-b-2 rounded-[3px] select-text'
                            >
                              {part}
                            </span>
                          )
                        }
                        if (index === 2) {
                          const cleanedPart = part.replace(/-\(weight-assign:[\d.]+\)-/g, '')
                          return (
                            <a
                              key={index}
                              href={cleanedPart}
                              target="_blank"
                              rel="noopener noreferrer"
                              className='text-[#1677ff] no-underline outline-none cursor-pointer transition-colors duration-300 border-0 p-0 bg-transparent select-text hover:text-[#69b1ff]'
                            >
                              {part}
                            </a>
                          )
                        }
                        if (index === 3) {
                          return (
                            <i key={index} className='text-[#7f8c8d] italic select-text'>
                              {part}
                            </i>
                          )
                        }
                        return null
                      })
                    }
                  </p>
                </div>
              )
            })
          }
        </div>
      </div>
    </main>
  )
}

export default Sidepanel
