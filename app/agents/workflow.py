"""
Updated Workflow Configuration with Date Filtering Options
Supports both filtered and unfiltered tender extraction
"""
import logging
from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END, START
from datetime import datetime

from .agent1 import TenderExtractionAgent
from .agent2 import TenderDetailAgent
from .agent3 import EmailComposerAgent

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    # Input
    page_content: str
    page_url: str
    page_id: int
    esg_keywords: List[str]
    credit_keywords: List[str]
    tender_repo: Any
    db: Any
    
    # NEW: Date filtering options
    enable_date_filtering: bool  # Whether to apply date filtering
    include_all_for_db1: bool   # Save all to DB1, filter for Agent 2
    
    # Agent 1 Output
    extracted_tenders: List[Dict[str, Any]]  # Raw tenders from Agent 1
    all_tenders: List[Dict[str, Any]]       # All tenders (unfiltered)
    filtered_tenders: List[Dict[str, Any]]   # Date-filtered tenders
    saved_basic_tenders: List[Any]          # Saved to DB1
    
    # Agent 2 Input/Output
    tenders_for_agent2: List[Dict[str, Any]]  # Tenders to process in Agent 2
    detailed_tenders: List[Dict[str, Any]]    # Detailed info from Agent 2
    saved_detailed_tenders: List[Any]        # Saved to DB2
    
    # Agent 3 Input/Output
    email_compositions: List[Dict[str, Any]]  # Composed emails from Agent 3
    
    # Status tracking
    agent1_completed: bool
    agent2_completed: bool
    agent3_completed: bool
    duplicates_checked: bool
    duplicate_count: int
    filtered_count: int  # NEW: How many were filtered by date
    error: str
    workflow_failed: bool

class TenderAgent:
    """Enhanced workflow orchestrator with configurable date filtering"""
    
    def __init__(self):
        self.agent1 = TenderExtractionAgent()
        self.agent2 = TenderDetailAgent()
        self.agent3 = EmailComposerAgent()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the enhanced workflow with date filtering options"""
        
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("agent1_extract", self._agent1_extract_node)
        workflow.add_node("check_duplicates", self._check_duplicates_node)
        workflow.add_node("save_to_db1", self._save_to_db1_node)
        workflow.add_node("agent2_details", self._agent2_details_node)
        workflow.add_node("save_to_db2", self._save_to_db2_node)
        workflow.add_node("agent3_compose", self._agent3_compose_node)
        
        # Define the workflow flow
        workflow.add_edge(START, "agent1_extract")
        workflow.add_edge("agent1_extract", "check_duplicates")
        workflow.add_conditional_edges(
            "check_duplicates",
            self._should_continue_pipeline,
            {
                "save_to_db1": "save_to_db1",
                "end": END
            }
        )
        workflow.add_edge("save_to_db1", "agent2_details")
        workflow.add_edge("agent2_details", "save_to_db2")
        workflow.add_edge("save_to_db2", "agent3_compose")
        workflow.add_edge("agent3_compose", END)
        
        return workflow.compile()
    
    async def _agent1_extract_node(self, state: WorkflowState) -> WorkflowState:
        """Enhanced Agent 1: Extract tenders with configurable date filtering"""
        try:
            logger.info("Agent 1: Starting enhanced tender extraction")
            logger.info(f"Date filtering: {'ENABLED' if state.get('enable_date_filtering', True) else 'DISABLED'}")
            
            # Extract all tenders first (for "All Tenders" view)
            all_tenders = await self.agent1.extract_and_categorize_tenders(
                page_content=state['page_content'],
                esg_keywords=state['esg_keywords'],
                credit_keywords=state['credit_keywords'],
                include_all_tenders=True  # Get everything first
            )
            
            # Apply date filtering if enabled
            if state.get('enable_date_filtering', True):
                filtered_tenders = await self.agent1.extract_and_categorize_tenders(
                    page_content=state['page_content'],
                    esg_keywords=state['esg_keywords'],
                    credit_keywords=state['credit_keywords'],
                    include_all_tenders=False  # Apply date filtering
                )
            else:
                filtered_tenders = all_tenders  # No filtering
            
            # Store both versions
            state['all_tenders'] = all_tenders
            state['filtered_tenders'] = filtered_tenders
            state['filtered_count'] = len(all_tenders) - len(filtered_tenders)
            
            # Decide what to use for further processing
            if state.get('include_all_for_db1', False):
                # Save all to DB1, but only process recent ones in Agent 2
                state['extracted_tenders'] = all_tenders
                state['tenders_for_agent2'] = filtered_tenders
            else:
                # Standard filtering - only process filtered tenders
                state['extracted_tenders'] = filtered_tenders
                state['tenders_for_agent2'] = filtered_tenders
            
            state['agent1_completed'] = True
            
            logger.info(f"Agent 1 completed:")
            logger.info(f"   All tenders found: {len(all_tenders)}")
            logger.info(f"   After date filtering: {len(filtered_tenders)}")
            logger.info(f"   Filtered out: {state['filtered_count']}")
            logger.info(f"   For DB1: {len(state['extracted_tenders'])}")
            logger.info(f"   For Agent 2: {len(state['tenders_for_agent2'])}")
            
            return state
            
        except Exception as e:
            logger.error(f"Agent 1 failed: {e}")
            state['extracted_tenders'] = []
            state['all_tenders'] = []
            state['filtered_tenders'] = []
            state['tenders_for_agent2'] = []
            state['agent1_completed'] = True
            state['error'] = str(e)
            return state
    
    async def _check_duplicates_node(self, state: WorkflowState) -> WorkflowState:
        """Check for duplicate tenders before saving to DB1"""
        try:
            logger.info("Checking for duplicate tenders...")
            
            extracted_tenders = state['extracted_tenders']
            filtered_tenders = []
            duplicate_count = 0
            
            for tender in extracted_tenders:
                title = tender.get('title', '')
                url = tender.get('url', '')
                
                if not title or not url:
                    logger.warning(f"Skipping tender with missing title or URL: {tender}")
                    continue
                
                is_duplicate = state['tender_repo'].check_duplicate_tender(
                    state['db'], title, url, state['page_id']
                )
                
                if is_duplicate:
                    duplicate_count += 1
                    logger.info(f"Duplicate found: {title[:50]}...")
                else:
                    filtered_tenders.append(tender)
                    logger.info(f"New tender: {title[:50]}...")
            
            state['extracted_tenders'] = filtered_tenders
            state['duplicate_count'] = duplicate_count
            state['duplicates_checked'] = True
            
            # Also update the Agent 2 list to remove duplicates
            agent2_filtered = []
            for tender in state['tenders_for_agent2']:
                url = tender.get('url', '')
                if any(t.get('url') == url for t in filtered_tenders):
                    agent2_filtered.append(tender)
            state['tenders_for_agent2'] = agent2_filtered
            
            logger.info(f"Filtered out {duplicate_count} duplicates.")
            logger.info(f"New tenders for DB1: {len(filtered_tenders)}")
            logger.info(f"New tenders for Agent 2: {len(state['tenders_for_agent2'])}")
            
            return state
            
        except Exception as e:
            logger.error(f"Duplicate checking failed: {e}")
            state['duplicates_checked'] = False
            state['error'] = str(e)
            return state
    
    def _should_continue_pipeline(self, state: WorkflowState) -> str:
        """Determine if pipeline should continue based on new tenders found"""
        new_tenders = state.get('extracted_tenders', [])
        
        if len(new_tenders) > 0:
            logger.info(f"Pipeline continuing: {len(new_tenders)} new tenders to process")
            return "save_to_db1"
        else:
            logger.info("No new tenders found. Ending pipeline.")
            return "end"
    
    async def _save_to_db1_node(self, state: WorkflowState) -> WorkflowState:
        """Save Agent 1 results to DB1 (basic tender info)"""
        try:
            logger.info("Saving basic tender info to DB1...")
            
            saved_tenders = []
            
            for tender_data in state['extracted_tenders']:
                tender = state['tender_repo'].save_tender(
                    state['db'],
                    page_id=state['page_id'],
                    title=tender_data['title'],
                    url=tender_data['url'],
                    tender_date=tender_data.get('deadline') or tender_data.get('date'),
                    category=tender_data['category'],
                    description=tender_data.get('description', '')
                )
                
                if tender:
                    saved_tenders.append(tender)
                    logger.info(f"Saved to DB1: {tender.title[:50]}... (ID: {tender.id})")
            
            state['saved_basic_tenders'] = saved_tenders
            
            logger.info(f"DB1 Save completed: {len(saved_tenders)} tenders saved")
            return state
            
        except Exception as e:
            logger.error(f"DB1 save failed: {e}")
            state['saved_basic_tenders'] = []
            state['error'] = str(e)
            return state
    
    async def _agent2_details_node(self, state: WorkflowState) -> WorkflowState:
        """Agent 2: Extract detailed info with date validation"""
        try:
            logger.info("Agent 2: Starting detailed tender extraction with date validation")
            
            tenders_to_process = state['tenders_for_agent2']
            skip_date_validation = not state.get('enable_date_filtering', True)
            
            logger.info(f"Processing {len(tenders_to_process)} tenders for details")
            logger.info(f"Date validation: {'DISABLED' if skip_date_validation else 'ENABLED'}")
            
            detailed_results = await self.agent2.process_multiple_tenders(
                tender_list=tenders_to_process,
                skip_date_validation=skip_date_validation
            )
            
            state['detailed_tenders'] = detailed_results
            state['agent2_completed'] = True
            
            # Log processing summary
            completed = len([t for t in detailed_results if t.get('processing_status') == 'completed'])
            skipped = len([t for t in detailed_results if t.get('processing_status') == 'skipped'])
            
            logger.info(f"Agent 2 completed:")
            logger.info(f"   Successfully processed: {completed}")
            logger.info(f"   Skipped (date validation): {skipped}")
            logger.info(f"   Total detailed tenders: {len(detailed_results)}")
            
            return state
            
        except Exception as e:
            logger.error(f"Agent 2 failed: {e}")
            state['detailed_tenders'] = []
            state['agent2_completed'] = True
            state['error'] = str(e)
            return state
    
    async def _save_to_db2_node(self, state: WorkflowState) -> WorkflowState:
        """Save Agent 2 results to DB2 (detailed tender info)"""
        try:
            logger.info("Saving detailed tender info to DB2...")
            
            saved_detailed = []
            
            for detailed_tender in state['detailed_tenders']:
                # Only save if processing was completed (not skipped)
                if detailed_tender.get('processing_status') != 'completed':
                    continue
                    
                try:
                    basic_tender = None
                    tender_url = detailed_tender.get('url')
                    
                    for saved_tender in state['saved_basic_tenders']:
                        if saved_tender.url == tender_url:
                            basic_tender = saved_tender
                            break
                    
                    if not basic_tender:
                        logger.warning(f"No matching basic tender found for URL: {tender_url}")
                        continue
                    
                    detailed_info = detailed_tender.get('detailed_info', {})
                    
                    detailed_tender_obj = state['tender_repo'].save_detailed_tender(
                        state['db'],
                        tender_id=basic_tender.id,
                        detailed_info=detailed_info
                    )
                    
                    if detailed_tender_obj:
                        saved_detailed.append(detailed_tender_obj)
                        logger.info(f"Saved to DB2: {basic_tender.title[:50]}... (Detail ID: {detailed_tender_obj.id})")
                
                except Exception as e:
                    logger.error(f"Failed to save detailed tender: {e}")
                    continue
            
            state['saved_detailed_tenders'] = saved_detailed
            
            logger.info(f"DB2 Save completed: {len(saved_detailed)} detailed tenders saved")
            return state
            
        except Exception as e:
            logger.error(f"DB2 save failed: {e}")
            state['saved_detailed_tenders'] = []
            state['error'] = str(e)
            return state
    
    async def _agent3_compose_node(self, state: WorkflowState) -> WorkflowState:
        """Agent 3: Compose intelligent email content for valid tenders only"""
        try:
            logger.info("Agent 3: Starting intelligent email composition")
            
            # Only compose emails for successfully processed tenders
            completed_tenders = [
                t for t in state['detailed_tenders'] 
                if t.get('processing_status') == 'completed'
            ]
            
            if not completed_tenders:
                logger.info("Agent 3: No completed tenders to compose emails for")
                state['email_compositions'] = []
                state['agent3_completed'] = True
                return state
            
            email_compositions = []
            
            # Group tenders by category for team-specific emails
            esg_tenders = [t for t in completed_tenders if t.get('category') in ['esg', 'both']]
            credit_tenders = [t for t in completed_tenders if t.get('category') in ['credit_rating', 'both']]
            
            # Compose emails for ESG tenders
            if esg_tenders:
                logger.info(f"Agent 3: Composing emails for {len(esg_tenders)} ESG tenders")
                esg_emails = await self.agent3.compose_multiple_emails(esg_tenders, "esg")
                email_compositions.extend(esg_emails)
            
            # Compose emails for Credit Rating tenders
            if credit_tenders:
                logger.info(f"Agent 3: Composing emails for {len(credit_tenders)} Credit Rating tenders")
                credit_emails = await self.agent3.compose_multiple_emails(credit_tenders, "credit_rating")
                email_compositions.extend(credit_emails)
            
            state['email_compositions'] = email_compositions
            state['agent3_completed'] = True
            
            logger.info(f"Agent 3 completed: {len(email_compositions)} email compositions created")
            logger.info(f"   Based on {len(completed_tenders)} successfully processed tenders")
            
            return state
            
        except Exception as e:
            logger.error(f"Agent 3 failed: {e}")
            state['email_compositions'] = []
            state['agent3_completed'] = True
            state['error'] = str(e)
            return state
    
    async def process_page(self, page_content: str, page_url: str, page_id: int, 
                          esg_keywords: List[str], credit_keywords: List[str],
                          tender_repo=None, db=None, 
                          enable_date_filtering: bool = True,
                          include_all_for_db1: bool = False) -> Dict[str, Any]:
        """
        Process a page through the enhanced pipeline with configurable date filtering
        
        Args:
            page_content: Main page content
            page_url: Page URL
            page_id: Page ID
            esg_keywords: ESG keywords
            credit_keywords: Credit rating keywords
            tender_repo: Tender repository
            db: Database session
            enable_date_filtering: Whether to apply date filtering
            include_all_for_db1: Whether to save all tenders to DB1 but filter for Agent 2
            
        Returns:
            Dict with processing results
        """
        
        initial_state: WorkflowState = {
            'page_content': page_content,
            'page_url': page_url,
            'page_id': page_id,
            'esg_keywords': esg_keywords,
            'credit_keywords': credit_keywords,
            'tender_repo': tender_repo,
            'db': db,
            
            # Date filtering configuration
            'enable_date_filtering': enable_date_filtering,
            'include_all_for_db1': include_all_for_db1,
            
            # Initialize empty results
            'extracted_tenders': [],
            'all_tenders': [],
            'filtered_tenders': [],
            'tenders_for_agent2': [],
            'saved_basic_tenders': [],
            'detailed_tenders': [],
            'saved_detailed_tenders': [],
            'email_compositions': [],
            
            # Initialize status
            'agent1_completed': False,
            'agent2_completed': False,
            'agent3_completed': False,
            'duplicates_checked': False,
            'duplicate_count': 0,
            'filtered_count': 0,
            'error': '',
            'workflow_failed': False
        }
        
        try:
            logger.info("Starting enhanced tender extraction pipeline with configurable date filtering...")
            logger.info(f"Configuration:")
            logger.info(f"   Date filtering: {'ENABLED' if enable_date_filtering else 'DISABLED'}")
            logger.info(f"   Save all to DB1: {'YES' if include_all_for_db1 else 'NO'}")
            
            # Run the enhanced workflow
            result = await self.workflow.ainvoke(initial_state)
            
            # Prepare final result
            final_result = {
                'filtered_tenders': result.get('saved_basic_tenders', []),
                'detailed_tenders': result.get('detailed_tenders', []),
                'email_compositions': result.get('email_compositions', []),
                'duplicates_checked': result.get('duplicates_checked', False),
                'duplicate_count': result.get('duplicate_count', 0),
                'filtered_count': result.get('filtered_count', 0),
                'agent1_completed': result.get('agent1_completed', False),
                'agent2_completed': result.get('agent2_completed', False),
                'agent3_completed': result.get('agent3_completed', False),
                'workflow_failed': bool(result.get('error')),
                'error': result.get('error', ''),
                'total_found': len(result.get('all_tenders', [])),
                'total_saved_basic': len(result.get('saved_basic_tenders', [])),
                'total_saved_detailed': len(result.get('saved_detailed_tenders', [])),
                'total_email_compositions': len(result.get('email_compositions', [])),
                'date_filtering_enabled': enable_date_filtering,
                'processing_summary': {
                    'all_tenders_found': len(result.get('all_tenders', [])),
                    'after_date_filtering': len(result.get('filtered_tenders', [])),
                    'after_duplicate_removal': len(result.get('saved_basic_tenders', [])),
                    'processed_by_agent2': len([
                        t for t in result.get('detailed_tenders', []) 
                        if t.get('processing_status') == 'completed'
                    ]),
                    'skipped_by_agent2': len([
                        t for t in result.get('detailed_tenders', []) 
                        if t.get('processing_status') == 'skipped'
                    ])
                }
            }
            
            logger.info(f"Enhanced pipeline completed successfully!")
            logger.info(f"Processing Summary:")
            logger.info(f"   All tenders found: {final_result['processing_summary']['all_tenders_found']}")
            logger.info(f"   After date filtering: {final_result['processing_summary']['after_date_filtering']}")
            logger.info(f"   After duplicate removal: {final_result['processing_summary']['after_duplicate_removal']}")
            logger.info(f"   Processed by Agent 2: {final_result['processing_summary']['processed_by_agent2']}")
            logger.info(f"   Skipped by Agent 2: {final_result['processing_summary']['skipped_by_agent2']}")
            logger.info(f"   Email compositions: {final_result['total_email_compositions']}")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Enhanced pipeline failed: {e}")
            return {
                'filtered_tenders': [],
                'detailed_tenders': [],
                'email_compositions': [],
                'duplicates_checked': False,
                'duplicate_count': 0,
                'filtered_count': 0,
                'agent1_completed': False,
                'agent2_completed': False,
                'agent3_completed': False,
                'workflow_failed': True,
                'error': str(e),
                'total_found': 0,
                'total_saved_basic': 0,
                'total_saved_detailed': 0,
                'total_email_compositions': 0,
                'date_filtering_enabled': enable_date_filtering,
                'processing_summary': {
                    'all_tenders_found': 0,
                    'after_date_filtering': 0,
                    'after_duplicate_removal': 0,
                    'processed_by_agent2': 0,
                    'skipped_by_agent2': 0
                }
            }