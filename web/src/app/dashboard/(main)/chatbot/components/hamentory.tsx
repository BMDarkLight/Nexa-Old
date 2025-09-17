import React from "react";
import { Input } from "@/components/ui/input";
import { ArrowUp } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
export default function StartChat() {
  return (
    <>
      <div className="h-[90vh]">
        <div className="flex items-center justify-center h-full w-[85%] mx-auto">
          <div className="chat-wrapper grid gap-5 w-full">
            {/* Chat Header */}
            <div className="chat-header ">
              <h2 className="font-bold text-xl">
                امروز می‌خواهید چه چیزی را تحلیل کنید؟
              </h2>
            </div>
            {/* Chatbot Input + btn + Agents Dropdown */}
            <div className="chat-input w-full">
              <div className="relative">
                <div className="absolute inset-y-2 right-3">
                  <Select >
                  <SelectTrigger className="w-[120px] text-xs rounded-xl ">
                    <SelectValue placeholder="انتخاب ایجنت" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="agent1">ایجنت ۱</SelectItem>
                    <SelectItem value="agent2">ایجنت ۲</SelectItem>
                    <SelectItem value="agent3">ایجنت ۳</SelectItem>
                  </SelectContent>
                </Select>
                </div>
                {/* chat Input */}
                <Input
                  id=""
                  placeholder="داده‌ها را متصل کنید و گفت‌وگو را شروع کنید!"
                  className="pt-18 pb-5 "
                />
                {/* Submit btn */}
                <button
                  type="button"
                  className="absolute inset-y-16 left-2 flex items-center justify-center bg-muted-foreground text-white w-6 h-6 rounded-full hover:opacity-90 transition duration-500"
                >
                  <ArrowUp size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
