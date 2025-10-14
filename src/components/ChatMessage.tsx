interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
}

const ChatMessage = ({ role, content }: ChatMessageProps) => {
  return (
    <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-6 py-4 ${
          role === 'user'
            ? 'bg-primary text-primary-foreground'
            : 'bg-secondary text-foreground border border-border'
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
};

export default ChatMessage;
