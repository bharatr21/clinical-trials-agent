"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Lightbulb } from "lucide-react";

const EXAMPLE_QUESTIONS = [
  "What are the most common conditions being studied?",
  "How many trials are currently in Phase 3?",
  "Which sponsors have the most active trials?",
  "Show me trials that started in the last 6 months",
  "How many clinical trials are being conducted in California?",
];

interface ExampleQuestionsProps {
  onSelect: (question: string) => void;
}

export function ExampleQuestions({ onSelect }: ExampleQuestionsProps) {
  return (
    <Card className="border-dashed">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          Try an example question
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((question) => (
            <Button
              key={question}
              variant="secondary"
              size="sm"
              onClick={() => onSelect(question)}
              className="text-xs h-auto py-1.5 px-3 font-normal"
            >
              {question}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
