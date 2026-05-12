/**
 * Tag/chip input with drag-and-drop reordering.
 *
 * Press Enter or comma to add a tag, click × to remove.
 * Tags can be reordered by dragging via @dnd-kit.
 */

import { useState } from "react";
import {
  DndContext,
  closestCenter,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  horizontalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { restrictToParentElement } from "@dnd-kit/modifiers";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ── SortableTag ─────────────────────────────────────────────────────────────

function SortableTag({ tag, onRemove }: { tag: string; onRemove: () => void }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: tag });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 10 : 0,
  };

  return (
    <span
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="inline-flex items-center gap-0.5 rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground cursor-grab active:cursor-grabbing"
    >
      {tag}
      <button
        type="button"
        aria-label={`Remove ${tag}`}
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20 focus:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        ×
      </button>
    </span>
  );
}

// ── TagInput ─────────────────────────────────────────────────────────────────

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
  fieldName?: string;
  onDuplicateConfirm?: (
    existingSkill: string,
    newSkill: string,
    fieldName: string,
  ) => Promise<boolean>;
  onBeforeAdd?: (tag: string) => boolean | Promise<boolean>;
}

export function TagInput({
  value,
  onChange,
  placeholder,
  className,
  fieldName,
  onDuplicateConfirm,
  onBeforeAdd,
}: TagInputProps) {
  const [inputValue, setInputValue] = useState("");

  // ── Tag commit logic ──────────────────────────────────────────────────────

  async function commit() {
    const tag = inputValue.trim();
    if (!tag) {
      setInputValue("");
      return;
    }
    if (value.includes(tag)) {
      toast.error("Skill already added");
      setInputValue("");
      return;
    }
    if (onBeforeAdd) {
      const allowed = await onBeforeAdd(tag);
      if (!allowed) {
        setInputValue("");
        return;
      }
    }
    if (onDuplicateConfirm) {
      const existingMatch = value.find(
        (v) => v.toLowerCase() === tag.toLowerCase(),
      );
      if (existingMatch) {
        const confirmed = await onDuplicateConfirm(
          existingMatch,
          tag,
          fieldName ?? "",
        );
        if (!confirmed) {
          setInputValue("");
          return;
        }
      }
    }
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

  // ── Drag-and-drop ─────────────────────────────────────────────────────────

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = value.indexOf(active.id as string);
    const newIndex = value.indexOf(over.id as string);
    if (oldIndex === -1 || newIndex === -1) return;
    onChange(arrayMove(value, oldIndex, newIndex));
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <DndContext
      collisionDetection={closestCenter}
      modifiers={[restrictToParentElement]}
      onDragEnd={handleDragEnd}
    >
      <div
        className={cn(
          "flex flex-wrap gap-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 min-h-10 cursor-text",
          className,
        )}
        style={{ touchAction: "none" }}
        onClick={(e) => {
          const input = (e.currentTarget as HTMLDivElement).querySelector(
            "input",
          );
          input?.focus();
        }}
      >
        <SortableContext
          items={value}
          strategy={horizontalListSortingStrategy}
        >
          {value.map((tag, i) => (
            <SortableTag
              key={tag}
              tag={tag}
              onRemove={() => removeTag(i)}
            />
          ))}
        </SortableContext>
        <input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={commit}
          placeholder={value.length === 0 ? placeholder : undefined}
          className="flex-1 min-w-24 bg-transparent outline-none placeholder:text-muted-foreground"
        />
      </div>
    </DndContext>
  );
}
