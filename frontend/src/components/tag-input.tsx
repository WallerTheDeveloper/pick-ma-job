/**
 * Tag/chip input with drag-and-drop reordering.
 *
 * Press Enter or comma to add a tag, click × to remove.
 * Tags can be reordered by dragging within the same field.
 *
 * When wrapped in a <TagInputProvider>, tags can also be dragged
 * between different TagInput fields (cross-field DnD).
 */

import { useState, useEffect, useCallback } from "react";
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
import { useDroppable } from "@dnd-kit/core";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import {
  useTagInputContext,
  buildTagId,
  buildContainerId,
} from "@/components/tag-input-provider";

// ── SortableTag ─────────────────────────────────────────────────────────────

function SortableTag({
  id,
  tag,
  onRemove,
}: {
  id: string;
  tag: string;
  onRemove: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  // Use explicit translate3d to avoid the widening/stretching bug
  // caused by CSS.Transform.toString including scale transforms.
  const style: React.CSSProperties = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        transition,
        opacity: isDragging ? 0.5 : 1,
        zIndex: isDragging ? 10 : 0,
      }
    : {
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
  /** Unique key for this field when using cross-field DnD. Required inside TagInputProvider. */
  fieldKey?: string;
  /** Display name for this field (used in duplicate error messages). */
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
  fieldKey,
  fieldName,
  onDuplicateConfirm,
  onBeforeAdd,
}: TagInputProps) {
  const provider = useTagInputContext();
  const isInProvider = provider !== null;
  const resolvedFieldKey = fieldKey ?? fieldName ?? "";

  const [inputValue, setInputValue] = useState("");

  // ── Register with provider for cross-field DnD ───────────────────────────

  const onChangeRef = useCallback(
    (tags: string[]) => onChange(tags),
    [onChange],
  );

  useEffect(() => {
    if (!isInProvider || !resolvedFieldKey) return;
    provider.registerField(resolvedFieldKey, {
      value,
      onChange: onChangeRef,
      fieldLabel: fieldName ?? resolvedFieldKey,
    });
    return () => {
      provider.unregisterField(resolvedFieldKey);
    };
  }, [
    isInProvider,
    resolvedFieldKey,
    value,
    onChangeRef,
    fieldName,
    provider,
  ]);

  // ── Droppable container for cross-field drops ───────────────────────────

  const containerId = isInProvider && resolvedFieldKey
    ? buildContainerId(resolvedFieldKey)
    : undefined;

  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: containerId ?? "unused",
    disabled: !isInProvider,
  });

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

  // ── Local drag-and-drop (when no provider) ─────────────────────────────

  function handleLocalDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = value.indexOf(active.id as string);
    const newIndex = value.indexOf(over.id as string);
    if (oldIndex === -1 || newIndex === -1) return;
    onChange(arrayMove(value, oldIndex, newIndex));
  }

  // ── Build sortable items ────────────────────────────────────────────────

  const sortableItems = isInProvider
    ? value.map((tag) => buildTagId(resolvedFieldKey, tag))
    : value;

  // ── Render ──────────────────────────────────────────────────────────────

  const containerDiv = (
    <div
      ref={isInProvider ? setDroppableRef : undefined}
      className={cn(
        "flex flex-wrap gap-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 min-h-10 cursor-text transition-colors",
        isOver && "border-primary/50 bg-primary/5",
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
      <SortableContext items={sortableItems} strategy={horizontalListSortingStrategy}>
        {value.map((tag, i) => {
          const sortableId = isInProvider
            ? buildTagId(resolvedFieldKey, tag)
            : tag;
          return (
            <SortableTag
              key={sortableId}
              id={sortableId}
              tag={tag}
              onRemove={() => removeTag(i)}
            />
          );
        })}
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
  );

  // When inside a provider, the DndContext is provided by TagInputProvider
  if (isInProvider) {
    return containerDiv;
  }

  // When standalone, render our own DndContext for internal reorder
  return (
    <DndContext
      collisionDetection={closestCenter}
      onDragEnd={handleLocalDragEnd}
    >
      {containerDiv}
    </DndContext>
  );
}