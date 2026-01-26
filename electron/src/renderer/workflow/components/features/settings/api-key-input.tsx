import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface ApiKeyInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function ApiKeyInput({ value, onChange, placeholder }: ApiKeyInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="flex gap-2">
      <Input
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || '输入 API Key'}
        className="font-mono flex-1"
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setVisible(!visible)}
        className="shrink-0"
      >
        {visible ? '隐藏' : '显示'}
      </Button>
    </div>
  );
}
