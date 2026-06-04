/* Compass-equivalent MongoDB connection check using the official Node driver. */

const { MongoClient } = require("mongodb");

function redact(uri) {
  return uri.replace(/\/\/([^:/@]+):([^@]+)@/, "//$1:***@");
}

async function main() {
  const uri = process.env.MONGODB_URI;
  if (!uri) {
    console.error("MONGODB_URI is required.");
    process.exit(2);
  }
  console.log(`URI: ${redact(uri)}`);
  const client = new MongoClient(uri, {
    serverSelectionTimeoutMS: 10000,
    connectTimeoutMS: 10000,
    socketTimeoutMS: 10000,
  });
  try {
    await client.connect();
    const result = await client.db("admin").command({ ping: 1 });
    console.log(JSON.stringify(result));
  } catch (error) {
    console.error(error && error.stack ? error.stack : error);
    process.exit(1);
  } finally {
    await client.close().catch(() => {});
  }
}

main();
