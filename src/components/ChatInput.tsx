import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Send, FileText } from 'lucide-react';

interface ChatInputProps {
  onSubmit: (videoUrl: string, question: string) => void;
  onFullSummary: (videoUrl: string) => void;
  isLoading: boolean;
}

const ChatInput = ({ onSubmit, onFullSummary, isLoading }: ChatInputProps) => {
  const [videoUrl, setVideoUrl] = useState('');
  const [question, setQuestion] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (videoUrl.trim() && question.trim() && !isLoading) {
      onSubmit(videoUrl.trim(), question.trim());
      setVideoUrl('');
      setQuestion('');
    }
  };

  const handleFullSummary = () => {
    if (videoUrl.trim() && !isLoading) {
      onFullSummary(videoUrl.trim());
      setVideoUrl('');
      setQuestion('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-2">
        <Input
          placeholder="YouTube video URL..."
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
          disabled={isLoading}
          className="bg-secondary border-border text-foreground placeholder:text-muted-foreground focus:ring-primary flex-1"
        />
        <Button
          type="button"
          onClick={handleFullSummary}
          disabled={isLoading || !videoUrl.trim()}
          className="bg-secondary hover:bg-secondary/80 text-foreground border border-border shadow-[0_0_15px_rgba(0,217,255,0.2)] hover:shadow-[0_0_25px_rgba(0,217,255,0.4)] transition-all"
        >
          <FileText className="h-5 w-5" />
        </Button>
      </div>
      <div className="flex gap-2">
        <Textarea
          placeholder="Ask a question about the video..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={isLoading}
          className="bg-secondary border-border text-foreground placeholder:text-muted-foreground focus:ring-primary min-h-[80px] resize-none"
        />
        <Button
          type="submit"
          disabled={isLoading || !videoUrl.trim() || !question.trim()}
          className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-[0_0_20px_rgba(0,217,255,0.3)] hover:shadow-[0_0_30px_rgba(0,217,255,0.5)] transition-all"
        >
          <Send className="h-5 w-5" />
        </Button>
      </div>
    </form>
  );
};

export default ChatInput;
