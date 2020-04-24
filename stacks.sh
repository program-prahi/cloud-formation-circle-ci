stacks=`aws cloudformation list-stacks --stack-status-filter "CREATE_COMPLETE"`
for i in $stacks
do 
    echo $i
done
