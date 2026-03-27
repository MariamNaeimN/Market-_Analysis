import json
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock environment variables before importing the module
os.environ['DYNAMODB_TABLE_NAME'] = 'test-table'
os.environ['ENVIRONMENT'] = 'test'

# Import the parser lambda module
import parser_lambda

class TestParserLambda:
    """Unit tests for Parser Lambda function"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.valid_analysis_results = {
            'parties': [
                {'name': 'Acme Corp', 'role': 'Vendor'},
                {'name': 'XYZ Inc', 'role': 'Client'}
            ],
            'dates': {
                'effectiveDate': '2024-01-01',
                'terminationDate': '2025-01-01'
            },
            'terms': [
                {'description': 'Payment terms', 'amount': '$10,000'}
            ],
            'obligations': [
                {'party': 'Acme Corp', 'obligation': 'Deliver services'}
            ],
            'risks': [
                {'type': 'Liability', 'description': 'Limited to contract value'}
            ]
        }
        
        self.valid_metadata = {
            'bucket': 'test-bucket',
            'key': 'contracts/test-contract.pdf',
            'timestamp': '2024-01-15T10:30:00Z'
        }
        
        self.valid_event = {
            'jobId': 'test-job-123',
            'analysisResults': self.valid_analysis_results,
            'metadata': self.valid_metadata
        }
    
    def test_validate_json_structure_success(self):
        """Test JSON validation with valid structure"""
        # Should not raise any exception
        parser_lambda.validate_json_structure(self.valid_analysis_results, 'test-job')
    
    def test_validate_json_structure_missing_fields(self):
        """Test JSON validation with missing required fields"""
        invalid_results = {
            'parties': [],
            'dates': {}
            # Missing: terms, obligations, risks
        }
        
        with pytest.raises(parser_lambda.ValidationError) as exc_info:
            parser_lambda.validate_json_structure(invalid_results, 'test-job')
        
        assert 'Missing required fields' in str(exc_info.value)
        assert 'terms' in str(exc_info.value)
        assert 'obligations' in str(exc_info.value)
        assert 'risks' in str(exc_info.value)
    
    def test_validate_json_structure_invalid_type(self):
        """Test JSON validation with invalid field types"""
        invalid_results = {
            'parties': 'not a list',  # Should be a list
            'dates': {},
            'terms': [],
            'obligations': [],
            'risks': []
        }
        
        with pytest.raises(parser_lambda.ValidationError) as exc_info:
            parser_lambda.validate_json_structure(invalid_results, 'test-job')
        
        assert "Field 'parties' must be a list" in str(exc_info.value)
    
    def test_validate_json_structure_not_dict(self):
        """Test JSON validation when input is not a dictionary"""
        with pytest.raises(parser_lambda.ValidationError) as exc_info:
            parser_lambda.validate_json_structure("not a dict", 'test-job')
        
        assert 'must be a dictionary' in str(exc_info.value)
    
    def test_extract_document_id(self):
        """Test document ID extraction from S3 key"""
        assert parser_lambda.extract_document_id('contracts/test-contract.pdf') == 'test-contract'
        assert parser_lambda.extract_document_id('test.pdf') == 'test'
        assert parser_lambda.extract_document_id('folder/subfolder/doc.png') == 'doc'
        assert parser_lambda.extract_document_id('no-extension') == 'no-extension'
        assert parser_lambda.extract_document_id('') == 'unknown'
    
    def test_extract_primary_party_name(self):
        """Test primary party name extraction"""
        # Test with dict format
        parties = [{'name': 'Acme Corp', 'role': 'Vendor'}]
        assert parser_lambda.extract_primary_party_name(parties) == 'Acme Corp'
        
        # Test with string format
        parties = ['Acme Corp']
        assert parser_lambda.extract_primary_party_name(parties) == 'Acme Corp'
        
        # Test with empty list
        assert parser_lambda.extract_primary_party_name([]) == 'unknown'
        
        # Test with None
        assert parser_lambda.extract_primary_party_name(None) == 'unknown'
    
    def test_transform_to_dynamodb_schema(self):
        """Test data transformation to DynamoDB schema"""
        result = parser_lambda.transform_to_dynamodb_schema(
            self.valid_analysis_results,
            self.valid_metadata,
            'test-job-123'
        )
        
        # Verify required fields
        assert 'insightId' in result
        assert 'documentId' in result
        assert 'uploadTimestamp' in result
        assert 'partyName' in result
        assert 'effectiveDate' in result
        assert 'jobId' in result
        assert 'analysisResults' in result
        assert 's3Metadata' in result
        assert 'processingTimestamp' in result
        assert 'environment' in result
        
        # Verify values
        assert result['documentId'] == 'test-contract'
        assert result['partyName'] == 'Acme Corp'
        assert result['effectiveDate'] == '2024-01-01'
        assert result['jobId'] == 'test-job-123'
        assert result['environment'] == 'test'
        assert result['s3Metadata']['bucket'] == 'test-bucket'
        assert result['s3Metadata']['key'] == 'contracts/test-contract.pdf'
    
    @patch('parser_lambda.table')
    def test_write_to_dynamodb_success(self, mock_table):
        """Test successful DynamoDB write operation"""
        mock_table.put_item = Mock()
        
        item = {
            'insightId': 'test-insight-123',
            'documentId': 'test-doc',
            'uploadTimestamp': 1234567890
        }
        
        # Should not raise any exception
        parser_lambda.write_to_dynamodb(item, 'test-job')
        
        # Verify put_item was called
        mock_table.put_item.assert_called_once_with(Item=item)
    
    @patch('parser_lambda.table')
    def test_write_to_dynamodb_failure(self, mock_table):
        """Test DynamoDB write operation failure"""
        mock_table.put_item = Mock(side_effect=Exception('DynamoDB error'))
        
        item = {'insightId': 'test-insight-123'}
        
        with pytest.raises(parser_lambda.DynamoDBWriteError) as exc_info:
            parser_lambda.write_to_dynamodb(item, 'test-job')
        
        assert 'DynamoDB write failed' in str(exc_info.value)
    
    @patch('parser_lambda.table')
    def test_lambda_handler_success(self, mock_table):
        """Test successful Lambda handler execution"""
        mock_table.put_item = Mock()
        
        result = parser_lambda.lambda_handler(self.valid_event, None)
        
        # Verify response
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['jobId'] == 'test-job-123'
        assert body['status'] == 'completed'
        assert 'insightId' in body
        
        # Verify DynamoDB was called
        mock_table.put_item.assert_called_once()
    
    @patch('parser_lambda.table')
    def test_lambda_handler_validation_error(self, mock_table):
        """Test Lambda handler with validation error"""
        invalid_event = {
            'jobId': 'test-job-123',
            'analysisResults': {'parties': []},  # Missing required fields
            'metadata': self.valid_metadata
        }
        
        result = parser_lambda.lambda_handler(invalid_event, None)
        
        # Verify error response
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['status'] == 'validation_failed'
        assert body['errorType'] == 'ValidationError'
        assert 'Missing required fields' in body['error']
        
        # Verify DynamoDB was not called
        mock_table.put_item.assert_not_called()
    
    @patch('parser_lambda.table')
    def test_lambda_handler_dynamodb_error(self, mock_table):
        """Test Lambda handler with DynamoDB error"""
        mock_table.put_item = Mock(side_effect=Exception('DynamoDB error'))
        
        result = parser_lambda.lambda_handler(self.valid_event, None)
        
        # Verify error response
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['status'] == 'failed'
        assert 'DynamoDB write failed' in body['error']
