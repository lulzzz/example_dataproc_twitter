#MIT License
#
#Copyright (c) 2017 Willian Fuks
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.


import json                                                                     
import datetime
import unittest                                                                 
import mock                                                                     
import shutil                                                                   
import os     

import webtest                                                                  


class TestWorkerBase(object):                                                   
    _source_config = 'tests/unit/data/gae/test_config.json'            
    _dest_config = 'gae/config.py'                                     
    _remove_config_flag = False                                                 
    @classmethod                                                                
    def load_worker_setup(cls):                                                 
        try:                                                                    
            import gae.worker as worker                                
        except ImportError:                                                     
            shutil.copyfile(cls._source_config, cls._dest_config)               
            cls._remove_config_flag = True                                      

        import gae.worker as worker                                    
        from gae import utils                                          
        cls.utils = utils                                                       
        cls.worker = worker                                                     

    @classmethod                                                                
    def clean_config(cls):                                                      
        if cls._remove_config_flag:                                             
            os.remove(cls._dest_config)

                                                                                
class TestWorkerService(unittest.TestCase, TestWorkerBase):                     
    @classmethod                                                                
    def setup_class(cls):                                                       
        cls.load_worker_setup()                                                 
        cls._test_app = webtest.TestApp(cls.worker.app)                         
                                                                                
    @classmethod                                                                
    def teardown_class(cls):                                                    
        cls.clean_config()                                                      
                                                                                
    @classmethod                                                                
    def load_mock_config(cls):                                                  
        return json.loads(open(cls._source_config).read().replace(              
            "config = ", ""))  

    @mock.patch('gae.worker.request')                                  
    @mock.patch('gae.utils.uuid')                                      
    @mock.patch('gae.worker.gcp_service')
    def test_export_pre_defined_date(self, service_mock, uuid_mock,
                                        request_mock):
        uuid_mock.uuid4.return_value = 'name'                              
        request_mock.form.get.return_value = '20171010'                         
        # this means that the config file is a pre-defined one              
        # so we need to replace it in this test                                 
        if not self._remove_config_flag:                                        
            self.worker.config = self.load_mock_config()                        

        query_job_body = self.utils.load_query_job_body("20171010",             
            **self.worker.config)                                               
        extract_job_body = self.utils.load_extract_job_body("20171010",         
            **self.worker.config)                                               
                                                                                
        job_mock = mock.Mock()                                                  
        service_mock.bigquery.execute_job.return_value = 'job' 
        response = self._test_app.post("/export_customers?date=20171010")           
                                                                                
        service_mock.bigquery.execute_job.assert_any_call(*['project123',
            query_job_body]) 
        service_mock.bigquery.poll_job.assert_called_once_with('job')
        service_mock.bigquery.execute_job.assert_any_call(*['project123',
            extract_job_body])                                                  
        self.assertEqual(response.status_int, 200)                              

    @mock.patch('gae.worker.request')                                  
    @mock.patch('gae.utils.uuid')                                      
    @mock.patch('gae.worker.gcp_service')
    def test_export_no_date(self, service_mock, uuid_mock, request_mock):
        uuid_mock.uuid4.return_value = 'name'                              
        request_mock.form.get.return_value = 'None'                         
        # this means that the config file is a pre-defined one              
        # so we need to replace it in this test                                 
        if not self._remove_config_flag:                                        
            self.worker.config = self.load_mock_config()                        
        today_str = (datetime.datetime.now() -
             datetime.timedelta(days=1)).strftime("%Y%m%d")

        query_job_body = self.utils.load_query_job_body(today_str,           
            **self.worker.config)               
        extract_job_body = self.utils.load_extract_job_body(today_str, 
            **self.worker.config)           
                                                                                
        job_mock = mock.Mock()                                                  
        service_mock.bigquery.execute_job.return_value = 'job' 
        response = self._test_app.post("/export_customers")   
                                                                                    
        service_mock.bigquery.execute_job.assert_any_call(*['project123',
            query_job_body])        
        service_mock.bigquery.execute_job.assert_any_call(*['project123',
            extract_job_body])                                                  
        self.assertEqual(response.status_int, 200)                      

    @mock.patch('gae.worker.scheduler')
    @mock.patch('gae.worker.request')                                  
    @mock.patch('gae.worker.gcp_service')
    def test_dataproc_dimsum(self, service_mock, request_mock,scheduler_mock):
        request_mock.form.get.return_value = '--days_init=3,days_end=2' 
        # this means that the config file is a pre-defined one              
        # so we need to replace it in this test                                 
        if not self._remove_config_flag:                                        
            self.worker.config = self.load_mock_config()                        

        response = self._test_app.post("/dataproc_dimsum")           
        service_mock.dataproc.build_cluster.assert_called_once_with(
            cluster_name='cluster_name',
            create_cluster={'master_type': 'instance-1',
                            'worker_type': u'instance-2',
                            'worker_num_instances': 2},
            project_id='project123',
            pyspark_job={'py_files': ['basename/1.py', 'basename/2.py'],
                         'bucket': 'bucket_name',
                         'default_args': ['--source_uri=gs://source/file.gz'],
                         'main_file': 'basename/main.py'},
            zone=u'region-1')

        service_mock.storage.upload_from_filenames.assert_called_once_with(
            bucket='bucket_name',
            default_args=['--source_uri=gs://source/file.gz'],
            main_file='basename/main.py', py_files=['basename/1.py',
                                                    'basename/2.py'])

        service_mock.dataproc.submit_pyspark_job.assert_called_with([
            '--days_init=3', 'days_end=2'], cluster_name='cluster_name',
             create_cluster={'master_type': 'instance-1',
                             'worker_type': 'instance-2',
                             'worker_num_instances': 2},
             project_id='project123',
             pyspark_job={'py_files': ['basename/1.py', 'basename/2.py'],
                          'bucket': 'bucket_name', 'default_args': [
                '--source_uri=gs://source/file.gz'],
                'main_file': 'basename/main.py'}, zone='region-1')

        service_mock.dataproc.delete_cluster.assert_called_once_with(
            cluster_name='cluster_name', create_cluster={
                'worker_type': 'instance-2', 'master_type': 'instance-1',
                'worker_num_instances': 2}, project_id='project123',
            pyspark_job={'py_files': ['basename/1.py', 'basename/2.py'],
                          'bucket': 'bucket_name', 'default_args': [
                '--source_uri=gs://source/file.gz'],
                'main_file': 'basename/main.py'}, zone='region-1')

        scheduler_mock.run.assert_called_once_with(
            {'url': '/prepare_datastore', 'target': u'df_service'}) 
