import { Prompts } from '@ant-design/x';
import { FireOutlined, CoffeeOutlined, SmileOutlined } from '@ant-design/icons';

import type { PromptsProps } from '@ant-design/x';

const App = ({onSend}) => {
  const items: PromptsProps['items'] = [
    {
      key: '6',
      icon: <CoffeeOutlined style={{ color: '#964B00' }} />,
      description: '执行远程任务',
      disabled: false,
    },
    {
      key: '7',
      icon: <SmileOutlined style={{ color: '#FAAD14' }} />,
      description: 'What are the secrets to maintaining a positive mindset?',
      disabled: false,
    },
    {
      key: '8',
      icon: <FireOutlined style={{ color: '#FF4D4F' }} />,
      description: 'How to stay calm under immense pressure?',
      disabled: false,
    },
  ];
  const onItemClick = (info: { data: PromptsProps['items'][0] }) => {
    const { description } = info.data;
    console.log(info);
    onSend(description);
  }
  return (
    <Prompts title="从这里开始一个新任务？" onItemClick={onItemClick} items={items} vertical />
  )
};

export default App;