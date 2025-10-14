import { useState } from 'react';
import { toast } from 'sonner';
import ChatMessage from '@/components/ChatMessage';
import ChatInput from '@/components/ChatInput';
import { Bot } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const Index = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hey! Drop a YouTube video URL and ask me anything about it.',
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (videoUrl: string, question: string) => {
    const userMessage = `Video: ${videoUrl}\n\nQuestion: ${question}`;
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_url: videoUrl,
          question: question,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch answer');
      }

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.answer || 'No answer received.' },
      ]);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to get answer. Make sure your API is running at 127.0.0.1:8000');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I couldn\'t fetch the answer. Check if the API is running.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFullSummary = async (videoUrl: string) => {
    const userMessage = `Full summary request for: ${videoUrl}`;
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_url: videoUrl,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch summary');
      }

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.summary || data.answer || 'No summary received.' },
      ]);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to get summary. Make sure your API is running at 127.0.0.1:8000/summary');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I couldn\'t fetch the summary. Check if the API is running.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="relative">
            <Bot className="h-8 w-8 text-primary" />
            <div className="absolute inset-0 blur-xl bg-primary/30 animate-pulse" />
          </div>
          <h1 className="text-2xl font-bold text-foreground">YouTube AI</h1>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-6 flex flex-col">
        <div className="flex-1 overflow-y-auto mb-6 space-y-4">
          {messages.map((message, index) => (
            <ChatMessage key={index} role={message.role} content={message.content} />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-secondary border border-border rounded-2xl px-6 py-4">
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-border pt-4">
          <ChatInput onSubmit={handleSubmit} onFullSummary={handleFullSummary} isLoading={isLoading} />
        </div>
      </main>
    </div>
  );
};

export default Index;
