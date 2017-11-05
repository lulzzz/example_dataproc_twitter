gcloud dataproc jobs submit pyspark --cluster=example-dataproc --py-files=base.py,factory.py,naive.py --bucket=lbanor run_jobs.py -- --days_init=3 --days_end=3 --source_uri=gs://lbanor/dataproc_example/data/{}/result.gz --inter_uri=gs://lbanor/dataproc_example/intermediary/{} --force=no --neighbor_uri=gs://lbanor/dataproc_example/naive/neighbor_matrix --algorithm=naive
