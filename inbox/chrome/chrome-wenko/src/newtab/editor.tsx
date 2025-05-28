"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Button, Input, Dropdown } from 'antd'
import type { MenuProps } from 'antd'
import './editor.css'
// import { Button } from "@/components/ui/button"
// import { Textarea } from "@/components/ui/textarea"
import {
  PlusOutlined as Plus,
  CloseOutlined as X,
  EditOutlined as Edit3,
  SaveOutlined as Save,
  MoreOutlined as MoreVertical,
} from "@ant-design/icons"
// import { Plus, X, Edit3, Save, MoreVertical } from "lucide-react"

const Textarea = Input.TextArea
interface CardData {
  id: string
  content: string
  parentId?: string
  level: number
}

export default function Editor() {
  // const items: MenuProps['items'] = [
  //   {
      
  //   }
  // ]
  const [cards, setCards] = useState<CardData[]>([
    { id: "1", content: "项目概述\n\n这是一个创新的写作工具项目，旨在提供更好的内容组织方式。", level: 0 },
    { id: "2", content: "核心功能\n\n• 多列布局\n• 卡片式编辑\n• 层级管理", level: 0 },
    { id: "3", content: "技术架构\n\n前端使用 React + TypeScript\n后端使用 Node.js", level: 0 },
    { id: "4", content: "用户界面设计\n\n简洁直观的设计理念", parentId: "1", level: 1 },
    { id: "5", content: "数据存储方案\n\n本地存储 + 云端同步", parentId: "1", level: 1 },
    { id: "6", content: "响应式布局\n\n适配各种屏幕尺寸", parentId: "4", level: 2 },
    { id: "7", content: "交互设计\n\n拖拽、快捷键支持", parentId: "4", level: 2 },
  ])

  const [editingCard, setEditingCard] = useState<string | null>(null)
  const [editContent, setEditContent] = useState("")
  const [selectedCard, setSelectedCard] = useState<string | null>(null)
  const [cardPositions, setCardPositions] = useState<
    Record<string, { x: number; y: number; width: number; height: number }>
  >({})

  const getCardsByLevel = (level: number) => {
    return cards.filter((card) => card.level === level)
  }

  const getChildCards = (parentId: string) => {
    return cards.filter((card) => card.parentId === parentId)
  }

  // 获取卡片的所有祖先ID
  const getAncestorIds = (cardId: string): string[] => {
    const card = cards.find((c) => c.id === cardId)
    if (!card || !card.parentId) return []
    return [card.parentId, ...getAncestorIds(card.parentId)]
  }

  // 获取卡片的所有后代ID
  const getDescendantIds = (cardId: string): string[] => {
    const children = cards.filter((c) => c.parentId === cardId)
    const descendants: string[] = []
    children.forEach((child) => {
      descendants.push(child.id)
      descendants.push(...getDescendantIds(child.id))
    })
    return descendants
  }

  // 判断卡片是否应该高亮
  const isCardHighlighted = (cardId: string): boolean => {
    if (!selectedCard) return true
    if (cardId === selectedCard) return true

    const ancestorIds = getAncestorIds(selectedCard)
    const descendantIds = getDescendantIds(selectedCard)

    return ancestorIds.includes(cardId) || descendantIds.includes(cardId)
  }

  const addCard = (level: number, parentId?: string) => {
    const newCard: CardData = {
      id: Date.now().toString(),
      content: "新卡片\n\n点击编辑内容...",
      level,
      parentId,
    }
    setCards([...cards, newCard])
  }

  const deleteCard = (cardId: string) => {
    // 递归删除子卡片
    const deleteCardAndChildren = (id: string) => {
      const children = cards.filter((card) => card.parentId === id)
      children.forEach((child) => deleteCardAndChildren(child.id))
      setCards((prev) => prev.filter((card) => card.id !== id))
    }
    deleteCardAndChildren(cardId)
  }

  const startEdit = (card: CardData) => {
    setEditingCard(card.id)
    setEditContent(card.content)
  }

  const saveEdit = () => {
    if (editingCard) {
      setCards((prev) => prev.map((card) => (card.id === editingCard ? { ...card, content: editContent } : card)))
      setEditingCard(null)
      setEditContent("")
    }
  }

  const cancelEdit = () => {
    setEditingCard(null)
    setEditContent("")
  }

  const maxLevel = Math.max(...cards.map((card) => card.level), -1) + 1

  // 渲染连接线
  const renderConnections = () => {
    if (!selectedCard) return null

    const selectedCardData = cards.find((c) => c.id === selectedCard)
    if (!selectedCardData) return null

    const connections = []
    const children = getChildCards(selectedCard)

    children.forEach((child) => {
      const parentPos = cardPositions[selectedCard]
      const childPos = cardPositions[child.id]

      if (parentPos && childPos) {
        const startX = parentPos.x + parentPos.width
        const startY = parentPos.y + parentPos.height / 2
        const endX = childPos.x
        const endY = childPos.y + childPos.height / 2

        const controlX = startX + (endX - startX) * 0.5

        connections.push(
          <path
            key={`${selectedCard}-${child.id}`}
            d={`M ${startX} ${startY} C ${controlX} ${startY}, ${controlX} ${endY}, ${endX} ${endY}`}
            stroke="rgba(255, 255, 255, 0.6)"
            strokeWidth="3"
            fill="none"
            className="transition-all duration-300"
          />,
        )
      }
    })

    return (
      <svg className="absolute inset-0 pointer-events-none z-10" style={{ width: "100%", height: "100%" }}>
        {connections}
      </svg>
    )
  }

  const updateCardPosition = useCallback(
    (cardId: string, pos: { x: number; y: number; width: number; height: number }) => {
      setCardPositions((prev) => ({
        ...prev,
        [cardId]: {
          x: cards.find((card) => card.id === cardId)?.level * 320 + pos.x,
          y: pos.y,
          width: pos.width,
          height: pos.height,
        },
      }))
    },
    [cards],
  )

  return (
    <div className="h-screen bg-[#3a7bba] overflow-hidden relative">
      {renderConnections()}

      {/* Main Editor Area */}
      <div className="flex h-full overflow-x-auto hide-scrollbar" style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}>
        {/* <style jsx>{`
          div::-webkit-scrollbar {
            display: none;
          }
        `}</style> */}

        {/* Render columns for each level */}
        {Array.from({ length: maxLevel + 1 }, (_, level) => {
          const levelCards = getCardsByLevel(level)
          const hasCards = levelCards.length > 0

          return (
            <div key={level} className="flex-shrink-0 w-80 h-full">
              {/* Column Content */}
              <div className="h-full overflow-y-auto hide-scrollbar" style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}>
                {/* <style jsx>{`
                  div::-webkit-scrollbar {
                    display: none;
                  }
                `}</style> */}

                {levelCards.map((card, index) => (
                  <CardComponent
                    key={card.id}
                    card={card}
                    isEditing={editingCard === card.id}
                    editContent={editContent}
                    onEdit={startEdit}
                    onSave={saveEdit}
                    onCancel={cancelEdit}
                    onDelete={deleteCard}
                    onContentChange={setEditContent}
                    onAddChild={() => addCard(level + 1, card.id)}
                    isHighlighted={isCardHighlighted(card.id)}
                    isSelected={selectedCard === card.id}
                    onSelect={() => setSelectedCard(selectedCard === card.id ? null : card.id)}
                    onPositionUpdate={(pos) => updateCardPosition(card.id, pos)}
                    isFirst={index === 0}
                  />
                ))}

                {/* 只有当前列有卡片时才显示添加按钮，或者是第一列 */}
                {(hasCards || level === 0) && (
                  <div className="p-2">
                    <Button
                      size="small"
                      onClick={() => addCard(level)}
                      className="w-full bg-white/20 hover:bg-white/30 text-white h-8 rounded"
                    >
                      <Plus className="h-4 w-4 mr-1" /> 添加卡片
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface CardComponentProps {
  card: CardData
  isEditing: boolean
  editContent: string
  onEdit: (card: CardData) => void
  onSave: () => void
  onCancel: () => void
  onDelete: (cardId: string) => void
  onContentChange: (content: string) => void
  onAddChild: () => void
  isHighlighted: boolean
  isSelected: boolean
  onSelect: () => void
  onPositionUpdate: (pos: { x: number; y: number; width: number; height: number }) => void
  isFirst: boolean
}

function CardComponent({
  card,
  isEditing,
  editContent,
  onEdit,
  onSave,
  onCancel,
  onDelete,
  onContentChange,
  onAddChild,
  isHighlighted,
  isSelected,
  onSelect,
  onPositionUpdate,
  isFirst,
}: CardComponentProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const prevPositionRef = useRef<string>("")

  useEffect(() => {
    if (cardRef.current) {
      const rect = cardRef.current.getBoundingClientRect()
      const parentRect = cardRef.current.offsetParent?.getBoundingClientRect()
      if (parentRect) {
        const newPos = {
          x: rect.left - parentRect.left,
          y: rect.top - parentRect.top,
          width: rect.width,
          height: rect.height,
        }

        const positionKey = `${newPos.x}-${newPos.y}-${newPos.width}-${newPos.height}`
        if (prevPositionRef.current !== positionKey) {
          prevPositionRef.current = positionKey
          onPositionUpdate(newPos)
        }
      }
    }
  }, [card.content, card.id, onPositionUpdate])

  return (
    <div
      ref={cardRef}
      className={`group bg-white transition-all duration-200 cursor-pointer relative z-20 ${isFirst ? "" : ""} ${
        isSelected ? "ring-2 ring-blue-500 shadow-lg" : "hover:shadow-md"
      } ${isHighlighted ? "opacity-100" : "opacity-30"}`}
      onClick={onSelect}
    >
      <div className="p-4">
        {/* Card content */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {isEditing ? (
              <div className="space-y-2">
                <Textarea
                  value={editContent}
                  onChange={(e) => onContentChange(e.target.value)}
                  className="min-h-[100px] resize-none border-gray-200"
                  placeholder="输入内容..."
                  onClick={(e) => e.stopPropagation()}
                />
                <div className="flex gap-2">
                  <Button
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation()
                      onSave()
                    }}
                  >
                    <Save className="h-3 w-3 mr-1" />
                    保存
                  </Button>
                  <Button
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation()
                      onCancel()
                    }}
                  >
                    取消
                  </Button>
                </div>
              </div>
            ) : (
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{card.content}</div>
            )}
          </div>

          {!isEditing && (
            <Dropdown trigger={['click']}>
              <Button icon={<MoreVertical />} size="small"></Button>
              {/* <DropdownMenuTrigger asChild>
                <Button
                  size="small"
                  className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 p-0 ml-2"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    onEdit(card)
                  }}
                >
                  <Edit3 className="h-4 w-4 mr-2" />
                  编辑
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    onAddChild()
                  }}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  添加子卡片
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(card.id)
                  }}
                  className="text-red-600"
                >
                  <X className="h-4 w-4 mr-2" />
                  删除
                </DropdownMenuItem>
              </DropdownMenuContent> */}
            </Dropdown>
          )}
        </div>
      </div>
    </div>
  )
}
