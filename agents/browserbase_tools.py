"""Simple BrowserbaseTools implementation based on agno cookbook example"""

import os
from typing import Optional, Dict, Any
from agno.tools.toolkit import Toolkit
from agno.tools.function import Function


class BrowserbaseTools(Toolkit):
    """
    Simplified BrowserbaseTools that creates sessions properly.
    Based on the agno cookbook example.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 project_id: Optional[str] = None,
                 **kwargs):
        """Initialize BrowserbaseTools with proper credentials"""
        
        # Get credentials from environment or parameters
        self.api_key = api_key or os.getenv("BROWSERBASE_API_KEY")
        self.project_id = project_id or os.getenv("BROWSERBASE_PROJECT_ID")
        
        if not self.api_key:
            raise ValueError("BROWSERBASE_API_KEY not provided")
        if not self.project_id:
            raise ValueError("BROWSERBASE_PROJECT_ID not provided")
        
        # Set environment variables to ensure they're available
        os.environ["BROWSERBASE_API_KEY"] = self.api_key
        os.environ["BROWSERBASE_PROJECT_ID"] = self.project_id
        
        # Try to initialize the agno BrowserbaseTools
        try:
            from agno.tools.browserbase import BrowserbaseTools as AgnoBrowserbaseTools
            self._tools = AgnoBrowserbaseTools(
                api_key=self.api_key,
                project_id=self.project_id,
                **kwargs
            )
            # Inherit all functions from the wrapped tools
            self.functions = self._tools.functions
        except Exception as e:
            print(f"Warning: Could not initialize agno BrowserbaseTools: {e}")
            print("Creating minimal implementation")
            # Create minimal implementation
            self._tools = None
            self.functions = []
            self._create_minimal_functions()
        
        super().__init__(name="browserbase_tools")
    
    def _create_minimal_functions(self):
        """Create minimal function implementations if agno tools fail"""
        
        # Navigate function
        def navigate_to_impl(url: str) -> Dict[str, Any]:
            """Navigate to a URL using Browserbase API directly"""
            import requests
            
            print(f"[BrowserbaseTools] Creating session for URL: {url}")
            
            # Create a session
            session_response = requests.post(
                "https://api.browserbase.com/v1/sessions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-BB-Project-ID": self.project_id,
                },
                json={"projectId": self.project_id}
            )
            
            if session_response.status_code != 201:
                return {"error": f"Failed to create session: {session_response.text}"}
            
            session_data = session_response.json()
            session_id = session_data["id"]
            print(f"[BrowserbaseTools] Session created: {session_id}")
            
            # Navigate to URL
            nav_response = requests.post(
                f"https://api.browserbase.com/v1/sessions/{session_id}/navigate",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={"url": url}
            )
            
            result = {
                "success": nav_response.status_code == 200,
                "session_id": session_id,
                "url": url
            }
            
            if result["success"]:
                print(f"[BrowserbaseTools] Successfully navigated to {url}")
            else:
                print(f"[BrowserbaseTools] Failed to navigate: {nav_response.text}")
                result["error"] = nav_response.text
            
            return result
        
        navigate_func = Function(
            name="navigate_to",
            description="Navigate to a URL in Browserbase",
            entrypoint=navigate_to_impl
        )
        
        self.functions.append(navigate_func)
    
    def navigate_to(self, url: str, **kwargs):
        """Navigate to a URL"""
        print(f"[BrowserbaseTools.navigate_to] Called with url='{url}', kwargs={kwargs}")
        
        # Filter out problematic parameters
        connect_url = kwargs.pop('connect_url', None)
        if connect_url:
            print(f"[BrowserbaseTools.navigate_to] Removed connect_url parameter: {connect_url}")
        
        # Validate URL
        if not url or url == 'connect_url' or not url.startswith(('http://', 'https://')):
            error_msg = f"Invalid URL provided: '{url}'"
            print(f"[BrowserbaseTools.navigate_to] {error_msg}")
            return {"error": error_msg}
        
        if self._tools:
            try:
                print(f"[BrowserbaseTools.navigate_to] Using agno BrowserbaseTools")
                return self._tools.navigate_to(url, **kwargs)
            except Exception as e:
                print(f"[BrowserbaseTools.navigate_to] Error in agno navigate_to: {e}")
                print(f"[BrowserbaseTools.navigate_to] Falling back to minimal implementation")
                # Fallback to minimal implementation
                return self.functions[0].entrypoint(url)
        else:
            print(f"[BrowserbaseTools.navigate_to] Using minimal implementation")
            # Use minimal implementation
            return self.functions[0].entrypoint(url)
    
    def screenshot(self, **kwargs):
        """Take a screenshot"""
        if self._tools:
            return self._tools.screenshot(**kwargs)
        else:
            return {"error": "Screenshot not implemented in minimal mode"}
    
    def click(self, selector: str, **kwargs):
        """Click an element"""
        if self._tools:
            return self._tools.click(selector, **kwargs)
        else:
            return {"error": "Click not implemented in minimal mode"}
    
    def fill(self, selector: str, value: str, **kwargs):
        """Fill a form field"""
        if self._tools:
            return self._tools.fill(selector, value, **kwargs)
        else:
            return {"error": "Fill not implemented in minimal mode"}
    
    def extract_text(self, **kwargs):
        """Extract text from the page"""
        if self._tools:
            return self._tools.extract_text(**kwargs)
        else:
            return {"error": "Extract text not implemented in minimal mode"}
    
    def evaluate(self, script: str, **kwargs):
        """Execute JavaScript on the page"""
        if self._tools:
            return self._tools.evaluate(script, **kwargs)
        else:
            return {"error": "Evaluate not implemented in minimal mode"}