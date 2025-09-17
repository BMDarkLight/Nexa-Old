import React, { Suspense } from "react";
import ChatbotPage from "../components/ChatbotPage";
import Chatbot from "../components/Chatbot";
export default function ChatbotMain(){
      return(
          <Suspense>
             <Chatbot />
          </Suspense>
      )
}