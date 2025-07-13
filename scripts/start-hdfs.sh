#!/bin/bash
set -e

NAMENODE_DIR="/opt/hadoop/data/nameNode"

if [ ! -d "$NAMENODE_DIR/current" ]; then
    echo "🚀 Formatting NameNode (first time)..."
    hdfs namenode -format -force -nonInteractive
else
    echo "✅ NameNode already formatted."
fi

echo "🔧 Starting HDFS NameNode Service..."
hdfs --daemon start namenode

echo "🔄 NameNode started. Keeping container alive..."
tail -f /dev/null
