class InMemoryDatabase:
    def __init__(self):
        self.records = {}  # Holds the record data
        self.modification_count = {}  # Keeps track of modification counts
        self.locks = {}  # Tracks which user has locked which record
        self.lock_queues = {}  # A queue for lock requests for each record

    def inc(self, key: str, field: str, value: int) -> None:
        # Do nothing since inc should not work without caller_id now
        return None

    def delete(self, key: str, field: str) -> None:
        # Do nothing since delete should not work without caller_id now
        return None

    def get(self, key: str, field: str) -> int | None:
        # Get operation is not affected by locks, works as usual
        if key in self.records and field in self.records[key]:
            return self.records[key][field]
        return None

    def set_or_inc_by_caller(self, key: str, field: str, value: int, caller_id: str) -> int | None:
        # Ensure the caller has the lock for this key
        if key not in self.locks or self.locks[key] != caller_id:
            return None

        # Proceed with the increment operation
        if key not in self.records:
            self.records[key] = {}
            self.modification_count[key] = 0

        if field in self.records[key]:
            self.records[key][field] += value
        else:
            self.records[key][field] = value

        self.modification_count[key] += 1
        return self.records[key][field]

    def delete_by_caller(self, key: str, field: str, caller_id: str) -> bool:
        # Ensure the caller has the lock for this key
        if key not in self.locks or self.locks[key] != caller_id:
            return False

        if key in self.records and field in self.records[key]:
            del self.records[key][field]
            self.modification_count[key] += 1

            # If the record is empty, delete it and the modification count
            if not self.records[key]:
                del self.records[key]
                del self.modification_count[key]
                del self.locks[key]  # Release the lock if the record is fully deleted
                self.lock_queues.pop(key, None)  # Clear the lock queue
            return True
        return False

    def lock(self, key: str, caller_id: str) -> str:
        # If the key does not exist, it's an invalid request
        if key not in self.records:
            return "invalid_request"

        # If the key is not locked, lock it for this caller
        if key not in self.locks:
            self.locks[key] = caller_id
            return "acquired"

        # If the key is already locked by this user, ignore
        if self.locks[key] == caller_id:
            return None

        # If it's locked by another user, add the caller to the queue
        if key not in self.lock_queues:
            self.lock_queues[key] = []

        if caller_id not in self.lock_queues[key]:
            self.lock_queues[key].append(caller_id)

        return "wait"

    def unlock(self, key: str) -> str:
        # If the key does not exist or is not locked, return None
        if key not in self.locks:
            return None

        # Release the lock
        del self.locks[key]

        # If there is a queue, pass the lock to the next user
        if key in self.lock_queues and self.lock_queues[key]:
            next_caller = self.lock_queues[key].pop(0)
            self.locks[key] = next_caller
            return "released"

        return "released"

    def top_n_keys(self, n: int) -> list[str]:
        # Sort keys by modification count (descending), and lexicographically for ties
        sorted_keys = sorted(self.modification_count.items(), 
                             key=lambda x: (-x[1], x[0]))

        # Format the output as required "<key>(<number_of_modifications>)"
        result = [f"{key}({count})" for key, count in sorted_keys]

        # Return the top n keys
        return result[:n]
