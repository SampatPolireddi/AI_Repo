from google import genai
from google.genai.types import (
    Tool, 
    FunctionDeclaration, 
    GenerateContentConfig,
    Content,
    Part
)
import pdfplumber
import re
import json

#Function/Tools for LLM
def extract_pdf_text(file_path):

    raw_text=[]

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            raw_text.append(page.extract_text())
    return '\n'.join(raw_text)

def classify_document(raw_text):
    text = re.sub(r'\n{3,}', '\n\n', raw_text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'^\s*Page \d+\s*$', '', text, flags=re.MULTILINE)
    cleaned_text = text.strip()
    
    # Simple keyword-based classification (backup logic)
    text_lower = cleaned_text.lower()
    
    if any(keyword in text_lower for keyword in ['account summary', 'checking', 'savings', 'deposits', 'withdrawals']):
        doc_type = "bank_statement"
        confidence = 0.85
    elif any(keyword in text_lower for keyword in ['credit card', 'previous balance', 'minimum payment', 'payment due']):
        doc_type = "credit_card"
        confidence = 0.85
    else:
        doc_type = "other"
        confidence = 0.60
    
    return {
        "type": doc_type,
        "confidence": confidence,
        "cleaned_text": cleaned_text
    }

def execute_function(function_name: str, arguments: dict):
    
    if function_name == "extract_pdf_text":
        return extract_pdf_text(arguments["file_path"])
    
    elif function_name == "classify_document":
        return classify_document(arguments["raw_text"])
    
    else:
        raise ValueError(f"Unknown function: {function_name}")

     
extract_pdf_declaration=FunctionDeclaration(
    name="extract_pdf_text",
    description="Extracts the raw text from the pdf file. Use this first to extract the text from the given pdf file",
    parameters={
        "type": "object",
        "properties":{
            "file_path": {
                "type": "string",
                "description": "Path to pdf file"
            }
        },
        "required":["file_path"]
    }
)

classify_declaration=FunctionDeclaration(
    name="classify_document",
    description="Cleans and classifies document as bank_statement, credit_card, or other. Returns cleaned text. Use this SECOND.",
    parameters={
        "type":"object",
        "properties":{
            "raw_text": {
                "type":"string",
                "description": "A list containing the raw text extracted from each page from the given pdf file"
            }
        },
        "required":["raw_text"]
    }
)

financial_analysis_tool=Tool(
    function_declarations=[
        extract_pdf_declaration,
        classify_declaration
    ]
)

def main(file_path:str):
    
    system_prompt="""
    You are an expert Financial Document Analysis Agent specialized in processing bank statements and credit card statements. 
    Your role is to intelligently analyze uploaded PDF documents, classify them, extract relevant information, 
    and present data in a clear, structured format.
    
    ##YOUR CAPABILITIES

    You have access to the following tools (call them in this order):

    1. extract_pdf_text(file_path)
    - Extracts raw text content from the PDF file
    - Input: file_path (string)
    - Returns: raw_text (string)
    - Use this FIRST to get the document content

    2. classify_document(raw_text)
    - Preprocesses and classifies the document
    - Input: raw_text (string) - the output from extract_pdf_text
    - Returns: {
        "type": "bank_statement" | "credit_card" | "other",
        "confidence": float (0.0 to 1.0),
        "cleaned_text": string (preprocessed version)
        }
    - Use this SECOND to identify document type
    - If type is "other", STOP and inform user


    ##YOUR OUTPUT:
    
    Your output should be neatly formatted and you should explain how you have classified the given document. And after that the output should contain the following also:
    
    1. If it is a bank statement:
        - account_holder_name: string
        - bank_name: string
        - account_number_last4: string
        - statement_period: {start_date: string, end_date: string}
        - opening_balance: float
        - closing_balance: float
        - total_deposits: float
        - total_withdrawals: float
        - transactions: [{date, description, amount, type, balance}]
        
    2. If it is a credit card statement/bill:
        - cardholder_name: string
        - card_issuer: string
        - card_last4: string
        - billing_cycle: {start_date: string, end_date: string}
        - previous_balance: float
        - payments_credits: float
        - purchases: float
        - fees_interest: float
        - new_balance: float
        - minimum_payment: float
        - payment_due_date: string
        - transactions: [{date, description, amount, category}]
   
    ## YOUR WORKFLOW (FOLLOW THIS EXACT SEQUENCE):

    STEP 1: EXTRACT PDF TEXT
    - Call: extract_pdf_text(file_path)
    - This returns the raw text content from the PDF
    - If extraction fails, inform user and stop

    STEP 2: CLASSIFY DOCUMENT
    - Call: classify_document(raw_text)
    - This function will:
    * Clean and preprocess the text
    * Analyze content to identify document type
    * Return: {
        "type": "bank_statement" | "credit_card" | "other",
        "confidence": 0.0 to 1.0,
        "cleaned_text": "preprocessed text"
        }
  
    - Decision point:
    * IF type is "other" → STOP processing and inform user this is not a financial statement
    * IF type is "bank_statement" or "credit_card" → Proceed to Step 3

    STEP 3: EXTRACT STRUCTURED DATA (only if Step 2 classified as bank or credit card)
    - Call: extract_structured_data(cleaned_text, document_type)
    - This function takes:
    * cleaned_text: The preprocessed text from classify_document
    * document_type: Either "bank_statement" or "credit_card"
    - Returns structured data matching the appropriate schema
    - Use bank_statement schema if document_type is "bank_statement"
    - Use credit_card schema if document_type is "credit_card"

    STEP 4: PRESENT RESULTS
    - Format the extracted data in clean, readable sections
    - Show document classification and confidence level
    - Display all extracted fields organized by category
    - Highlight important dates or amounts
    - Note any missing fields or extraction issues
                
    ## YOUR BEHAVIOR GUIDELINES

    1. **Be decisive but transparent:** Make classification decisions confidently, but always show your confidence level
 
    2. **Fail gracefully:** If extraction is impossible or document quality is poor, explain what went wrong

    3. **Privacy-aware:** Only show last 4 digits of account/card numbers, redact sensitive information

    4. **User-focused:** Present data clearly, highlight actionable information (due dates, large transactions)

    5. **Accurate over complete:** Better to have fewer fields extracted correctly than many fields with errors

    6. **Think step-by-step:** After each tool call, reason about the results before proceeding

    7. **Adaptive:** If first extraction strategy fails, try alternative approaches

    ## ERROR HANDLING

    - **PDF extraction fails:** Inform user the PDF may be corrupted or password-protected
    - **Text is garbled:** Suggest document may be scanned image, might need OCR
    - **No transactions found:** Note this clearly, may be a summary statement
    - **Validation fails:** Present data anyway but clearly mark discrepancies

    ## IMPORTANT REMINDERS:
    - Validate data before presenting
    - Format output for human readability, not raw JSON

    Begin by asking the user to upload their PDF document, or if a document is already provided, start your analysis immediately.   
    """
    
    client= genai.Client()
    
    chat=client.chats.create(
        model="gemini-2.5-flash",
        config=GenerateContentConfig(
            tools=[financial_analysis_tool],
            temperature=0.1,
            system_instruction=system_prompt
        )
    )
    
    print("🤖 Agent starting analysis...\n")
    
    response=chat.send_message(
        f"Please analyse this document at: {file_path}"
    )
    
    max_iteration=10
    final_result=None
    
    for i in range(0,max_iteration):
        
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                
                if part.function_call:
                    function_call= part.function_call
                    function_name= function_call.name
                    function_args= dict(function_call.args)
                    
                    try:
                        result=execute_function(function_name,function_args)
                        
                        response=chat.send_message(
                            Part.from_function_response(
                                name=function_name,
                                response={"result":result}
                            )
                        )
                    
                    except Exception as e:
                        response=chat.send_message(
                            Part.from_function_response(
                                name=function_name,
                                response={"error": str (e)}
                            )
                        )
                    break
                
                elif part.text:
                    print("=" * 70)
                    print("ANALYSIS COMPLETE:")
                    print("=" * 70)
                    print(part.text)
                    return part.text  
        
        else:
            break
    
    if final_result is None:
        raise Exception("Agent did not produce final output")
    
    return final_result
        
if __name__ == "__main__":
    file_path= "path/statement.pdf"
    
    try:
        result = main(file_path) 
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()