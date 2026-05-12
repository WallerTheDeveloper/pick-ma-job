/** Tag/chip input — press Enter or comma to add a tag, click × to remove. */

import { useState } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
  fieldName?: string;
  onDuplicateConfirm?: (existingSkill: string, newSkill: string, fieldName: string) => Promise<boolean>;
}

export function TagInput({ value, onChange, placeholder, className, fieldName, onDuplicateConfirm }: TagInputProps) {
  const [inputValue, setInputValue] = useState("");

  async function commit() {
    const tag = inputValue.trim();
    if (!tag) {
      setInputValue("");
      return;
    }

    // 1. Exact match — block immediately
    if (value.includes(tag)) {
      toast.error("Skill already added");
      setInputValue("");
      return;
    }

    // 2. Case-insensitive match in same field — show confirmation
    if (onDuplicateConfirm) {
      const existingMatch = value.find(v => v.toLowerCase() === tag.toLowerCase());
      if (existingMatch) {
        const confirmed = await onDuplicateConfirm(existingMatch, tag, fieldName ?? "");
        if (!confirmed) {
          setInputValue("");
          return;
        }
      }
    }

    // 3. No duplicate — add
    onChange([...value, tag]);
    setInputValue("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      commit();
    } else if (e.key === ",") {
      e.preventDefault();
      commit();
    } else if (e.key === "Backspace" && !inputValue && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  function removeTag(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  return (
    <div
      className={cn(
        "flex flex-wrap gap-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 min-h-10 cursor-text",
        className,
      )}
      onClick={(e) => {
        const input = (e.currentTarget as HTMLDivElement).querySelector("input");
        input?.focus();
      }}
    >
      {value.map((tag, i) => (
        <span
          key={tag}
          className="inline-flex items-center gap-0.5 rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground"
        >
          {tag}
          <button
            type="button"
            aria-label={`Remove ${tag}`}
            onClick={(e) => {
              e.stopPropagation();
              removeTag(i);
            }}
            className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20 focus:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            ×
          </button>
        </span>
      ))}
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commit}
        placeholder={value.length === 0 ? placeholder : undefined}
        className="flex-1 min-w-24 bg-transparent outline-none placeholder:text-muted-foreground"
      />
    </div>
  );
}